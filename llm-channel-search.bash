#!/bin/bash
read -p "What channel URL? (/videos): " channel
#read -p "Date? (YYYYMMDD?): " date
read -p "What are you looking for?: " question
mkdir -p /dev/shm/llm-channel-search/ || exit 1
cd /dev/shm/llm-channel-search/ || exit 1
temp="0.0"

mapfile -t ids < <(yt-dlp --date "${date}" --flat-playlist -J "${channel}" | jq -r '.entries[].id' )

for id in "${ids[@]}" ; do
   url="https://www.youtube.com/watch?v=${id}"
   yt-dlp --no-warnings -q --skip-download --sub-format srv3 --write-auto-subs "${url}" -o video || exit 1
   title=$(yt-dlp --no-warnings -q --skip-download --get-title "${url}")

   cat video.en.srv3 | html2text > /dev/shm/llm-channel-search/video.txt
   echo -n "${url}: " | tee -a /dev/shm/llm-channel-search/channel-output.txt
   llm-python-file.py /dev/shm/llm-channel-search/video.txt "You are a helpful assistant."  "The following is a youtube video transcription for a video named \`${title}\`."  "Does this help answer the question or topic of \`${question}\`?  Start your answer with \`Yes\` or \`No\`." "${temp}" | sed -e 's/\\n/\n/g' -e "s/\\'/'/g" -e "s/^'$//g" -e 's/\\//g' -e "s/'$//g" | tee -a /dev/shm/llm-channel-search/channel-output.txt

done | grep "Yes"
