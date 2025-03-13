#!/bin/bash
url=$1
temp_dir=$(mktemp -d -p /dev/shm/)
cd "$temp_dir" || exit 1

#curl -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36' -s -L "${url}" | html2text > "${temp_dir}/llm-website-summary.txt"
lynx -dump "${url}" > "${temp_dir}/llm-website-summary.txt"
read -p "What is the task for ${url}?: " task

while [ -n "${task}" ] ; do
  llm-python-file.py "${temp_dir}/llm-website-summary.txt" "You are a helpful assistant." "The following is the website output of URL: \`${url}\`." "${task}" "0.0"
  read -p "What is the task for ${url}?: " task
done

# Clean up the temporary directory
rm -rf "$temp_dir"
