#!/usr/bin/env bash

grep '"type":' out/*.json | grep -vE "string|boolean|snowflake|_structure|_enum|integer|{|timestamp|any|map"