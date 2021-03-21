#!/usr/bin/env bash

start=$(date +%s%N)

# Output path
output_dir="./out"
echo ">> Cleaning up $output_dir..."
rm -rf "$output_dir"
mkdir -pv "$output_dir"

# Git commit info
git_info=$(git -C $1 log -1 --pretty="%H %aI")

echo ">> Processing API docs from $1..."
echo ">> Latest commit: $git_info"

# Base paths
docs_path="$1/docs"
resources_path="$docs_path/resources"
topics_path="$docs_path/topics"

# Necessary topics
gateway_path="$topics_path/Gateway.md"
permissions_path="$topics_path/Permissions.md"
teams_path="$topics_path/Teams.md"
oauth_path="$topics_path/OAuth2.md"

function process() {
    echo ">> Processing file: $1"
    basename=$(basename $1 | sed -e 's/.md//g' | awk '{print tolower($0)}')
    xml="<div>$(pandoc -f markdown $1 >&1)</div>"
    tables_and_headers=$(echo $xml | xmllint --format - | xpath -q -e "/div/*[(self::h6[not(contains(@id, 'example'))] or self::table)]")
    echo "<div>$tables_and_headers</div>" | python process.py > "$output_dir/$basename.json"
}

process $gateway_path
process $permissions_path
process $teams_path
process $oauth_path

find $resources_path -maxdepth 1 -type f -print0 | while IFS= read -r -d $'\0' file; do
    process "$file"
done

# TODO: lol
echo ""
echo ""
echo ""
echo ""
echo ""
echo ""
echo ""
echo ""
echo ""
echo ""

elixir_path="$output_dir/elixir"
mkdir -pv $elixir_path

echo ">> Generating Elixir structs in $elixir_path..."

function process_elixir() {
    echo ">> Processing JSON -> Elixir: $1"
    basename=$(basename $1 | sed -e 's/.json//g' | awk '{print tolower($0)}')
    echo ">> Sending output to $elixir_path/$basename.ex"
    cat $1 | python process_elixir.py $basename "$git_info" > "$elixir_path/$basename.ex"
}

find $output_dir -maxdepth 1 -type f -print0 | while IFS= read -r -d $'\0' file; do
    process_elixir "$file"
done

runtime=$((($(date +%s%N) - $start)/1000000))

echo ">> Done! Took ${runtime}ms"
