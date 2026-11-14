"""Patch scripts/run_atlas.py to register Milestone 13T Mission OS routes."""
import sys

def patch():
    with open("scripts/run_atlas.py", "r", encoding="utf-8") as f:
        content = f.read()

    # 1. Patch imports
    import_target = "    settlement_reset_api,\n    APIError,"
    import_repl = (
        "    settlement_reset_api,\n"
        "    mission_os_status_api,\n"
        "    mission_os_create_api,\n"
        "    mission_os_advance_api,\n"
        "    mission_os_dispatch_command_api,\n"
        "    mission_os_inject_event_api,\n"
        "    mission_os_flagship_run_api,\n"
        "    mission_os_replay_verify_api,\n"
        "    mission_os_dossier_api,\n"
        "    APIError,"
    )
    if import_target in content:
        content = content.replace(import_target, import_repl)
    else:
        print("Import target not found!")
        sys.exit(1)

    # 2. Patch do_GET
    get_target = '            elif clean_path in ("/api/settlement/replay", "/api/v1/settlement/replay"):\n                res = settlement_replay_export_api()\n                self.send_json_response(res, 200)\n                return'
    get_repl = (
        get_target + "\n"
        '            elif clean_path in ("/api/mission-os/status", "/api/v1/mission-os/status"):\n'
        '                res = mission_os_status_api()\n'
        '                self.send_json_response(res, 200)\n'
        '                return\n'
        '            elif clean_path in ("/api/mission-os/dossier", "/api/v1/mission-os/dossier"):\n'
        '                res = mission_os_dossier_api()\n'
        '                self.send_json_response(res, 200)\n'
        '                return\n'
        '            elif clean_path in ("/api/mission-os/replay", "/api/v1/mission-os/replay"):\n'
        '                res = mission_os_replay_verify_api()\n'
        '                self.send_json_response(res, 200)\n'
        '                return\n'
        '            elif clean_path in ("/api/mission-os/flagship/run", "/api/v1/mission-os/flagship/run"):\n'
        '                res = mission_os_flagship_run_api()\n'
        '                self.send_json_response(res, 200)\n'
        '                return'
    )
    if get_target in content:
        content = content.replace(get_target, get_repl)
    else:
        print("GET target not found!")
        sys.exit(1)

    # 3. Patch do_POST
    post_target = '            elif clean_path in ("/api/settlement/reset", "/api/v1/settlement/reset"):\n                result = settlement_reset_api()\n                self.send_json_response(result, 200)\n                return'
    post_repl = (
        post_target + "\n"
        '            elif clean_path in ("/api/mission-os/create", "/api/v1/mission-os/create"):\n'
        '                result = mission_os_create_api(payload)\n'
        '                self.send_json_response(result, 200)\n'
        '                return\n'
        '            elif clean_path in ("/api/mission-os/advance", "/api/v1/mission-os/advance"):\n'
        '                result = mission_os_advance_api(payload)\n'
        '                self.send_json_response(result, 200)\n'
        '                return\n'
        '            elif clean_path in ("/api/mission-os/dispatch-command", "/api/v1/mission-os/dispatch-command"):\n'
        '                result = mission_os_dispatch_command_api(payload)\n'
        '                self.send_json_response(result, 200)\n'
        '                return\n'
        '            elif clean_path in ("/api/mission-os/inject-event", "/api/v1/mission-os/inject-event"):\n'
        '                result = mission_os_inject_event_api(payload)\n'
        '                self.send_json_response(result, 200)\n'
        '                return\n'
        '            elif clean_path in ("/api/mission-os/flagship/run", "/api/v1/mission-os/flagship/run"):\n'
        '                result = mission_os_flagship_run_api()\n'
        '                self.send_json_response(result, 200)\n'
        '                return'
    )
    if post_target in content:
        content = content.replace(post_target, post_repl)
    else:
        print("POST target not found!")
        sys.exit(1)

    with open("scripts/run_atlas.py", "w", encoding="utf-8") as f:
        f.write(content)
    print("Successfully patched scripts/run_atlas.py with Mission OS routes!")

if __name__ == "__main__":
    patch()
