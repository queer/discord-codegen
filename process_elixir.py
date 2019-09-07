#!/usr/bin/env python

from datetime import datetime
import json
import sys
import time

def now():
    return int(round(time.time() * 1000))

start = now()

stdin_lines = sys.stdin.readlines()
stdin = "".join(stdin_lines)
module = sys.argv[1]
data = json.loads(stdin)

def camel(snake):
    components = snake.split('_')
    return ''.join(x.title() for x in components)

def snake(s):
    return s.replace(" ", "_").replace("-", "_").lower()

def quote(s):
    try:
        int(s)
        return s
    except ValueError:
        try:
            int(s, 16)
            return s
        except ValueError:
            return f'"{s}"'

def unquote(s):
    return s.replace("'", "").replace('"', '')

def derive_type(t):
    ts = t["type"]
    optional = t["optional"]
    nullable = t["nullable"]
    res = ""
    if ts == "boolean":
        res += "boolean()"
    elif ts == "string":
        res += "String.t()"
    elif ts == "snowflake":
        res += "String.t()"
    elif ts == "integer":
        res += "integer()"
    elif ts.startswith("array"):
        res += "list()"
    elif ts == "map":
        res += "map()"
    elif ts == "timestamp":
        res += "String.t()"
    elif ts == "any":
        res += "term()"
    elif ts == "snowflake | array<snowflake>":
        res += "String.t() | list()"
    elif ts == "activity_assets_structure":
        res += "Discord.Gateway.ActivityAssets.t()"
    elif ts == "activity_party_structure":
        res += "Discord.Gateway.ActivityParty.t()"
    elif ts == "activity_secrets_structure":
        res += "Discord.Gateway.ActivitySecrets.t()"
    elif ts == "activity_structure":
        res += "Discord.Gateway.Activity.t()"
    elif ts == "activity_timestamps_structure":
        res += "Discord.Gateway.ActivityTimestamps.t()"
    elif ts == "client_status_structure":
        res += "Discord.Gateway.ClientStatus.t()"
    elif ts == "embed_author_structure":
        res += "Discord.Channel.EmbedAuthor.t()"
    elif ts == "embed_footer_structure":
        res += "Discord.Channel.EmbedFooter.t()"
    elif ts == "embed_image_structure":
        res += "Discord.Channel.EmbedImage.t()"
    elif ts == "embed_provider_structure":
        res += "Discord.Channel.EmbedProvider.t()"
    elif ts == "embed_thumbnail_structure":
        res += "Discord.Channel.EmbedThumbnail.t()"
    elif ts == "embed_video_structure":
        res += "Discord.Channel.EmbedVideo.t()"
    elif ts == "guild_member_structure":
        res += "Discord.Guild.GuildMember.t()"
    elif ts == "integration_account_structure":
        res += "Discord.Guild.IntegrationAccount.t()"
    elif ts == "message_activity_structure":
        res += "Discord.Channel.MessageActivity.t()"
    elif ts == "message_application_structure":
        res += "Discord.Channel.MessageApplication.t()"
    elif ts == "message_reference_structure":
        res += "Discord.Channel.MessageReference.t()"
    elif ts == "optional_audit_entry_info_structure":
        res += "Discord.AuditLog.OptionalAuditEntryInfo.t()"
    elif ts == "user_structure":
        res += "Discord.User.t()"
    elif ts == "role_structure":
        res += "Discord.Permissions.Role.t()"
    else:
        print("## Warning: Unknown type:", ts, "assuming term()", file=sys.stderr)
        res += "term()"
    
    if optional or nullable:
        res += " | nil"

    return res

def extract_type(ts, f):
    if ts == "activity_assets_structure":
        return f'Discord.Gateway.ActivityAssets.create(from["{f}"])'
    elif ts == "activity_party_structure":
        return f'Discord.Gateway.ActivityParty.create(from["{f}"])'
    elif ts == "activity_secrets_structure":
        return f'Discord.Gateway.ActivitySecrets.create(from["{f}"])'
    elif ts == "activity_structure":
        return f'Discord.Gateway.Activity.create(from["{f}"])'
    elif ts == "activity_timestamps_structure":
        return f'Discord.Gateway.ActivityTimestamps.create(from["{f}"])'
    elif ts == "client_status_structure":
        return f'Discord.Gateway.ClientStatus.create(from["{f}"])'
    elif ts == "embed_author_structure":
        return f'Discord.Channel.EmbedAuthor.create(from["{f}"])'
    elif ts == "embed_footer_structure":
        return f'Discord.Channel.EmbedFooter.create(from["{f}"])'
    elif ts == "embed_image_structure":
        return f'Discord.Channel.EmbedImage.create(from["{f}"])'
    elif ts == "embed_provider_structure":
        return f'Discord.Channel.EmbedProvider.create(from["{f}"])'
    elif ts == "embed_thumbnail_structure":
        return f'Discord.Channel.EmbedThumbnail.create(from["{f}"])'
    elif ts == "embed_video_structure":
        return f'Discord.Channel.EmbedVideo.create(from["{f}"])'
    elif ts == "guild_member_structure":
        return f'Discord.Guild.GuildMember.create(from["{f}"])'
    elif ts == "integration_account_structure":
        return f'Discord.Guild.IntegrationAccount.create(from["{f}"])'
    elif ts == "message_activity_structure":
        return f'Discord.Channel.MessageActivity.create(from["{f}"])'
    elif ts == "message_application_structure":
        return f'Discord.Channel.MessageApplication.create(from["{f}"])'
    elif ts == "message_reference_structure":
        return f'Discord.Channel.MessageReference.create(from["{f}"])'
    elif ts == "optional_audit_entry_info_structure":
        return f'Discord.AuditLog.OptionalAuditEntryInfo.create(from["{f}"])'
    elif ts == "user_structure":
        return f'Discord.User.create(from["{f}"])'
    elif ts == "role_structure":
        return f'Discord.Permissions.Role.create(from["{f}"])'
    else:
        return f'from["{f}"]'

out = f"defmodule Discord.{camel(module)} do\n"
out += "{{stats}}\n"
out += "  # Requires typed_struct: https://github.com/ejpcmac/typed_struct\n"
out += "  # Get it on Hex: https://hex.pm/packages/typed_struct\n"
out += "  use TypedStruct\n"
out += "\n"

enums_generated = 0
structs_generated = 0

out += "{{enum_header}}"
for (key, value) in data.items():
    if key.endswith("enum"):
        enum_name = key.replace("_enum", "")
        out += f"  # Enum {enum_name}\n"
        for enum_key, enum_value in value.items():
            if isinstance(enum_value, str):
                out_enum_value = enum_value
                if "<<" in enum_value:
                    # This is evil but it solves the problem
                    out_enum_value = str(eval(enum_value))
                out += f"  def {enum_name}_{snake(enum_key)}, do: {quote(out_enum_value)}\n"
            elif isinstance(enum_value, dict):
                if "desc" in enum_value:
                    # :hahayes:
                    desc = enum_value["desc"]
                    out += f'  @doc "{unquote(desc)}"\n'
                inner_value = enum_value["value"]
                if "<<" in inner_value:
                    # This is evil but it solves the problem
                    inner_value = str(eval(inner_value))
                out += f"  def {enum_name}_{snake(enum_key)}, do: {quote(inner_value)}\n"
        out += "\n"
        enums_generated += 1

if enums_generated > 0:
    out = out.replace("{{enum_header}}", "  # Enums\n")
else:
    out = out.replace("{{enum_header}}", "")

out += "{{struct_header}}"
for (key, value) in data.items():
    if key.endswith("structure"):
        module_name = camel(key).replace("Structure", "")
        if module_name == camel(module):
            out += f"  # {module} struct {key}\n"
            out += '  @typedoc """\n'
            for (field, field_data) in value.items():
                if "$" in field:
                    field = quote(field)
                out += f"  * `:{field}`: {field_data['desc']}\n"
            out += '  """\n'
            out += "  typedstruct do\n"
            for (field, field_data) in value.items():
                if "$" in field:
                    field = quote(field)
                out += f"    field :{field}, {derive_type(field_data)}\n"
            out += "  end\n\n"
            out += "  def create(from) do\n"
            out += f"    %Discord.{camel(module)}" + "{\n"
            for (field, field_data) in value.items():
                if "$" in field:
                    field = quote(field)
                out += f'      {field}: {extract_type(field_data["type"], unquote(field))},\n'
            out += "    }\n"
            out += "  end\n"
        else:
            out += f"  # {module} struct {key}\n"
            out += f"  defmodule {module_name} do\n"
            out += '    @typedoc """\n'
            for (field, field_data) in value.items():
                if "$" in field:
                    field = quote(field)
                out += f"    * `:{field}`: {field_data['desc']}\n"
            out += '    """\n'
            out += "    typedstruct do\n"
            for (field, field_data) in value.items():
                if "$" in field:
                    field = quote(field)
                out += f"      field :{field}, {derive_type(field_data)}\n"
            out += "    end\n\n"
            out += "    def create(from) do\n"
            out += f"      %Discord.{camel(module)}.{module_name}" + "{\n"
            for (field, field_data) in value.items():
                if "$" in field:
                    field = quote(field)
                out += f'        {field}: {extract_type(field_data["type"], unquote(field))},\n'
            out += "      }\n"
            out += "    end\n"
            out += "  end\n\n"
        structs_generated += 1

if structs_generated > 0:
    out = out.replace("{{struct_header}}", "  # Structs\n")
else:
    out = out.replace("{{struct_header}}", "")

# Remove a trailing newline
if (structs_generated > 0 or (structs_generated == 0 and enums_generated > 0)) and out[:-2] == "\n\n":
    out = out[:-1]
out += "end"

end = now()

out = out.replace("{{stats}}", f"""
  # Processed {str(len(stdin_lines))} lines of JSON in {end - start}ms.
  # Generated at {datetime.utcnow()}.
  # Generated from discord-api-docs {sys.argv[2]}.
  # Generated {enums_generated} enums.
  # Generated {structs_generated} structs.
"""[1:])

print(out)