#!/usr/bin/env python

import json
import re
import sys
import xml.etree.ElementTree as ET

data = sys.stdin.readlines()
root = ET.fromstring("".join(data))

skippable_sections = [
    "Gateway Payload Structure",
    "Gateway Commands",
    "Gateway Events",
    "Identify Structure",
    "Resume Structure",
    "Query String Params",
    # Yes, really.
    "Querystring Params",
    # Yes, REALLY.
    "Query String Parameters",
    # I can't believe this one is real.
    "Get Invite URL Parameters",
    # Yep, you guessed it.
    "Gateway URL Params",
    "JSON Response",
    "JSON Params",
    "JSON/Form Params",
    "Sharding Formula",
    "Widget Style Options",
    "Limits",
    "Params",
    "Gateway Versions"
]

last = None
table = {}

def full_text(tag):
    # TODO: Missing space between text/tail?
    return ((tag.text or "") + ''.join((t.text or "") + (t.tail or "") for t in tag)).replace("\\n", "").strip()

def typeinfo(name, type_):
    return {
        "optional": name.endswith("?"),
        "nullable": type_.startswith("?")
    }

def dict_concat(a, b):
    out = {}
    out.update(a)
    out.update(b)
    return out

def snake(s):
    return s.replace(" ", "_").replace("-", "_").lower()

def clarify_type(t, section=None):
    t = t.replace("?", "")
    if section is not None:
        if section == "activity_structure":
            if t == "timestamps object":
                return "activity_timestamps_structure"
            elif t == "party object":
                return "activity_party_structure"
            elif t == "assets object":
                return "activity_assets_structure"
            elif t == "secrets object":
                return "activity_secrets_structure"
        elif section == "channel_structure":
            if t == "type":
                return "channel_types_enum"
        elif section == "message_structure":
            if t == "type":
                return "message_types_enum"
            elif t == "message activity object":
                return "message_activity_structure"
            elif t == "message application object":
                return "message_application_structure"
            elif t == "message_reference object":
                return "message_reference_structure"
        elif section == "integration_structure":
            if t == "account object":
                return "integration_account_structure"
        elif section == "ready_event_structure":
            if t.startswith("array of two integers"):
                return "array<integer>"
            elif t == "array":
                return "array<any>"
        elif section == "gateway_status_update_structure":
            if t == "activity object":
                return "activity_structure"
        elif section == "presence_update_event_structure":
            if t == "activity object":
                return "activity_structure"
        elif section == "guild_request_members_structure":
            if t == "snowflake or array of snowflakes":
                return "snowflake | array<snowflake>"
        elif section == "audit_log_change_structure":
            if t == "mixed":
                return "any"
        elif section == "audit_log_change_key":
            if t == "integer (channel type) or string":
                return "channel_types_enum | string"
        elif section == "audit_log_entry_structure":
            if t == "audit log event":
                return "audit_log_events_enum"
            elif t == "optional audit entry info":
                return "optional_audit_entry_info_structure"
        elif section == "connection_structure":
            if t == "array":
                return "array<any>"
        elif section == "guild_emojis_update_event_structure":
            if t == "array":
                return "array<emoji_structure>"
        else:
            return clarify_type(t)
    elif t == "user object":
        return "user_structure"
    elif t == "guild member object":
        return "guild_member_structure"
    elif t.startswith("array of"):
        cleaned = re.sub(r"objects.*$", "", t.replace("array of", "")).strip()
        snaked = snake(cleaned)
        type_name = f"{snaked}_structure"
        if type_name == "snowflake_structure" or type_name == "snowflakes_structure":
            type_name = "snowflake"
        elif type_name == "Unavailable_Guild_structure":
            type_name = type_name.lower()
        return f"array<{type_name}>"
    elif t.startswith("embed ") and t.endswith(" object"):
        return t.replace(" ", "_").replace("object", "structure")
    elif t == "ISO8601 timestamp":
        return "timestamp"
    elif t == "a role object":
        return "role_structure"
    elif t == "a user object":
        return "user_structure"
    elif t == "int":
        return "integer"
    elif t == "client_status object":
        return "client_status_structure"
    elif (t.startswith("partial ") or t.startswith("a partial ")) and t.endswith(" object"):
        # The docs contain a TON of stuff that doesn't exactly specify types in
        # a manner that can be easily parsed out. In that case, we just call it
        # a plain map and move on.
        return "map"
    else:
        return t
    # Yes, this is actually needed as a final catch-all
    if section is not None:
        return clarify_type(t)
    else:
        return t

def deunicode(s):
    return s.replace("\u2018", "'").replace("\u2019", "'").replace("\u201c", '"').replace("\u201d", '"')

def fix_struct_name(name, cols=3):
    name = deunicode(name)
    if cols == 2 and not name.endswith("_enum"):
        name += "_enum"
    elif cols == 3:
        if name.endswith("_fields"):
            name = name.replace("_fields", "_structure")
        if not name.endswith("_structure"):
            name += "_structure"
    elif name == "optional_audit_entry_info":
        return "optional_audit_entry_info_structure"
    return name

def is_actually_enum(name):
    return name in [
        "channel_types_structure",
        "message_flags_structure",
        "visibility_types_structure",
        "premium_types_structure",
        "verification_level_structure",
        "bitwise_permission_flags"
    ]

for child in root:
    if child.tag == "h6":
        if last is None:
            last = child.text
        else:
            print("Warning: Setting last to", child.text, "but it was never reset from", last, file=sys.stderr)
            last = child.text
    elif child.tag == "table":
        if last is None:
            # If we hit a table we don't recognize, we try to traverse it to
            # figure out if we can recognize it. We do this immediately, then
            # have another `last is None` check to make sure that it actually
            # is none and not something we had to guess from heuristics.
            client_status_keys_found = []
            client_status_keys_expected = ["desktop?", "web?", "mobile?"]
            for t in child:
                if t.tag == "tbody":
                    for tr in t:
                        for x in tr:
                            if x.text in client_status_keys_expected:
                                client_status_keys_found.append(x.text)
            if set(client_status_keys_found) == set(client_status_keys_expected):
                # Not an accurate name, but it's Close Enough:tm: and should
                # get it to generate correctly for us
                last = "Client Status Structure"
        if last is None:
            print("Warning: Skipping unknown table due to no last header", file=sys.stderr)
            last = None
        elif last not in skippable_sections:
            # print("Processing section:", last, file=sys.stderr)
            col_count = 0
            for table_chunk in child:
                if table_chunk.tag == "thead":
                    for header_row in table_chunk:
                        for header_col in header_row:
                            col_count += 1
                elif table_chunk.tag == "tbody":
                    # Name | Value
                    # Field | Type | Description
                    rows = list(table_chunk)
                    struct = {}
                    section_name = fix_struct_name(last.lower().replace(" ", "_"), cols=col_count)
                    enum = False
                    if col_count == 3 or col_count == 4:
                        if is_actually_enum(section_name):
                            # This is an enum, but we can't autodetect that.
                            enum = True
                            section_name = fix_struct_name(last.lower().replace(" ", "_"), cols=2)
                    if "json" not in section_name:
                        for row in rows:
                            cols = list(row)
                            if col_count == 2:
                                if last == "User Flags" or last == "Premium Types":
                                    name = snake(full_text(cols[1]))
                                    value = full_text(cols[0])
                                    struct[name] = value
                                elif last == "Premium Types" or last == "Visibility Types":
                                    name = snake(cols[1].text)
                                    value = cols[0].text
                                    desc = full_text(cols[2])
                                    struct[name] = {
                                        "value": value,
                                        "desc": desc
                                    }
                                    pass
                                elif last == "Guild Features":
                                    name = cols[0].text
                                    value = cols[0].text
                                    desc = cols[1].text
                                    struct[name] = {
                                        "value": value,
                                        "desc": desc
                                    }
                                else:
                                    name = cols[0].text
                                    value = cols[1].text
                                    struct[name] = value
                            elif col_count == 3:
                                name = cols[0].text
                                # Make hyperlinks inside of types work
                                type_ = full_text(cols[1])
                                desc = full_text(cols[2])
                                real_name = name.replace("?", "").replace("*", "")
                                real_type = type_.replace("?", "")
                                struct[real_name] = dict_concat({
                                    ("value" if enum else "type"): deunicode(clarify_type(real_type, section=section_name)),
                                    "desc": "" if desc is None else deunicode(desc.strip())
                                }, typeinfo(name, type_))
                            elif col_count == 4:
                                if last == "Activity Types":
                                    # This is an enum, but we can't autodetect that.
                                    section_name = fix_struct_name(last.lower().replace(" ", "_"), cols=2)
                                    # ID | Name | Format | Example
                                    id_ = cols[0].text
                                    name = cols[1].text
                                    format_ = cols[2].text
                                    example = deunicode(cols[3].text)
                                    struct[snake(name)] = {
                                        "value": id_,
                                        "desc": f"{format_} - {example}"
                                    }
                                elif last == "Optional Audit Entry Info":
                                    # Field | Type | Description | Action type
                                    field = cols[0].text
                                    type_ = full_text(cols[1])
                                    desc = deunicode(full_text(cols[2]))
                                    action_type = cols[3].text
                                    struct[field] = dict_concat({
                                        "type": clarify_type(type_),
                                        "desc": desc,
                                        "action_type": action_type
                                    }, typeinfo(field, type_))
                                elif last == "Audit Log Change Key":
                                    # Name | Object changed | Type | Description
                                    name = cols[0].text
                                    object_changed = full_text(cols[1])
                                    type_ = full_text(cols[2])
                                    desc = deunicode(full_text(cols[3]))
                                    struct[name] = dict_concat({
                                        "object_changed": object_changed,
                                        "type": clarify_type(type_),
                                        "desc": desc
                                    }, typeinfo(name, type_))
                                elif last == "User Structure":
                                    # Field | Type | Description | Required OAuth scope
                                    field = cols[0].text
                                    type_ = full_text(cols[1])
                                    desc = deunicode(full_text(cols[2]))
                                    oauth_scope = full_text(cols[3])
                                    struct[field] = dict_concat({
                                        "type": clarify_type(type_),
                                        "desc": desc,
                                        "oauth_scope": oauth_scope
                                    }, typeinfo(field, type_))
                                elif last == "Bitwise Permission Flags":
                                    name = full_text(cols[0]).replace("*", "")
                                    value = full_text(cols[1])
                                    description = full_text(cols[2])
                                    channel_types = cols[3].text
                                    struct[name] = {
                                        "value": value,
                                        "description": description,
                                        "channel_types": channel_types
                                    }
                                else:
                                    print(f"Warning: Unknown 4-column section: {last}", file=sys.stderr)
                            else:
                                print(f"Warning: Unknown column count: {col_count} (expected 2 or 3), section = {last}", file=sys.stderr)
                        table[section_name] = struct
                    else:
                        print(f"Warning: Skipping json section: {last}", file=sys.stderr)
        last = None
    else:
        print(f"Unknown tag: {child.tag}", file=sys.stderr)

print(json.dumps(table, indent=2))