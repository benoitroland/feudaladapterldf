#!/usr/bin/env python3
# vim: tw=100 foldmethod=expr
"""Simulate how the user would be created. 
"""
import sys
import json

# Must be before the first ldf_adapter import
from feudal_globalconfig import globalconfig

from ldf_adapter import User
from ldf_adapter.cmdline_params import args


def main():
    try:
        data = json.load(sys.stdin)
    except json.decoder.JSONDecodeError as e:
        message = "Cannot decode the input json. Please verify the input!"
        print(message)
        sys.exit(2)

    try:  # User.__init__ tries finding userinfo in data["user"]["userinfo"]
        user = User(data)
    except KeyError:
        try:
            data = {"user": {"userinfo": data}}
            user = User(data)
        except KeyError:
            print("cannot find required information in input json.")
            sys.exit(3)
        except Exception as e:
            print(f"Unhandled Exception: {e}")
            raise

    print(f"User: {user.data.username}")
    for grp in sorted(user.data.groups):
        print(f"   {grp}")


if __name__ == "__main__":
    sys.exit(main())
