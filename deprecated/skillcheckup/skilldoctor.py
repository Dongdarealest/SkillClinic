"""Deprecated skillcheckup package: SkillDoctor is now SkillClinic.

This is the final skillcheckup release. It installs the new skillclinic
package and hands over to it, so anyone still installing the old name
ends up running the new tool, with a pointer to the new name.
"""

import sys


def main(argv=None):
    print("skillcheckup is deprecated: SkillDoctor is now SkillClinic.",
          file=sys.stderr)
    print("Install the skillclinic package and use the skillclinic command.",
          file=sys.stderr)
    from skillclinic import main as clinic_main
    sys.argv[0] = "skillclinic"
    return clinic_main(argv)


if __name__ == "__main__":
    raise SystemExit(main())
