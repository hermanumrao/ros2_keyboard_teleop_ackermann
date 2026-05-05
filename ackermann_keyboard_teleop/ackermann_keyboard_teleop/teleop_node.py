import rclpy
from rclpy.node import Node
from std_msgs.msg import String

import sys
import termios
import tty
import select
import time

PUBLISH_RATE = 20.0  # Hz
TIMEOUT = 0.5  # seconds


class KeyboardTeleop(Node):

    def __init__(self):
        super().__init__("ackermann_keyboard_teleop")

        self.publisher_ = self.create_publisher(String, "/motor_command", 10)
        self.timer = self.create_timer(
            1.0 / PUBLISH_RATE, self.publish_commands)

        # State
        self.speed = 0
        self.direction = "F"

        self.servo1 = 90  # rear
        self.servo2 = 90  # front

        self.speed_step = 25
        self.steer_step = 15

        self.last_key_time = time.time()

        self.get_logger().info(
            "W/S: speed | X: slow down | A/D: steer (reversed) | Z/C: rear steer | SPACE: stop"
        )

        self.settings = termios.tcgetattr(sys.stdin)

    def get_key(self):
        tty.setraw(sys.stdin.fileno())
        rlist, _, _ = select.select([sys.stdin], [], [], 0.01)

        key = ""
        if rlist:
            key = sys.stdin.read(1)

        termios.tcsetattr(sys.stdin, termios.TCSADRAIN, self.settings)
        return key

    def update_state(self, key):
        now = time.time()

        if key:
            self.last_key_time = now

        if key == "w":
            self.direction = "F"
            self.speed = min(250, self.speed + self.speed_step)

        elif key == "s":
            self.direction = "B"
            self.speed = min(250, self.speed + self.speed_step)

        elif key == "x":
            self.speed = max(0, self.speed - self.speed_step)

        # 🔁 REVERSED steering
        elif key == "a":  # should go right now
            self.servo2 = min(180, self.servo2 + self.steer_step)

        elif key == "d":  # should go left now
            self.servo2 = max(0, self.servo2 - self.steer_step)

        # 🔧 Servo1 control (rear)
        elif key == "z":
            self.servo1 = max(0, self.servo1 - self.steer_step)

        elif key == "c":
            self.servo1 = min(180, self.servo1 + self.steer_step)

        elif key == " ":
            self.speed = 0

        # ⛔ Deadman timeout
        if (now - self.last_key_time) > TIMEOUT:
            self.speed = 0

    def publish_commands(self):
        key = self.get_key()
        self.update_state(key)

        # Commands
        speed_cmd = f"{self.direction}{self.speed}"
        servo1_cmd = f"SERVO1{self.servo1}"
        servo2_cmd = f"SERVO2{self.servo2}"

        # Publish
        for cmd in [speed_cmd, servo1_cmd, servo2_cmd]:
            msg = String()
            msg.data = cmd
            self.publisher_.publish(msg)

        self.get_logger().info(
            f"{speed_cmd} | S1:{self.servo1} | S2:{self.servo2}",
            throttle_duration_sec=0.5,
        )


def main(args=None):
    rclpy.init(args=args)
    node = KeyboardTeleop()

    try:
        rclpy.spin(node)
    except KeyboardInterrupt:
        pass

    node.destroy_node()
    rclpy.shutdown()


if __name__ == "__main__":
    main()
