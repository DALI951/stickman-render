"""Numeric rig readout - the numbers that ASCII art distorts.

    python tools/rigdump.py jab_wind jab_hit ...
"""

import sys

sys.path.insert(0, ".")

from src import rig  # noqa: E402


def dump(names):
    hdr = ("pose".ljust(12) + "fistR_x".rjust(9) + "fistR_y".rjust(9)
           + "elbR_x".rjust(9) + "footR_x".rjust(9) + "footL_x".rjust(9)
           + "head_y".rjust(8) + "lowest_y".rjust(9))
    print(hdr)
    print("-" * len(hdr))
    for n in names:
        j = rig.fk(rig.pose(n))
        low = min(j["ftL"][1], j["ftR"][1])
        print(n.ljust(12)
              + f"{j['haR'][0]:+9.3f}" + f"{j['haR'][1]:9.3f}"
              + f"{j['elR'][0]:+9.3f}" + f"{j['ftR'][0]:+9.3f}"
              + f"{j['ftL'][0]:+9.3f}" + f"{j['head'][1]:8.3f}"
              + f"{low:+9.4f}")


def main():
    names = sys.argv[1:] or list(rig.POSES.keys())
    dump(names)


if __name__ == "__main__":
    main()
