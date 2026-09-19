import json

from security import opencode_config


def test_chat_denies_edit_and_generic_shell():
    cfg = json.loads(opencode_config('chat'))
    rules = cfg['permissions']
    assert {'action': 'edit', 'resource': '*', 'effect': 'deny'} in rules
    assert {'action': 'shell', 'resource': '*', 'effect': 'deny'} in rules


def test_exec_allows_edit_but_not_git_push():
    cfg = json.loads(opencode_config('exec'))
    rules = cfg['permissions']
    assert {'action': 'edit', 'resource': '*', 'effect': 'allow'} in rules
    assert not any(
        r['action'] == 'shell'
        and r['resource'].startswith('git push')
        and r['effect'] == 'allow'
        for r in rules
    )
