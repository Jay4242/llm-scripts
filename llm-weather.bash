#!/bin/bash

#Set zip code.
zip=""  #Enter Zip code in quotes.
#Next line tries to set it automatically based on the IP address.
#location=$(curl -s https://ipinfo.io/json) && zip=$(echo $location | jq -r '.postal')

#Makes cURL calls to the localLLM
curllm(){

   system=$1
   temp=$2
   prompt=$3

   #Debug lines.
   #echo "System is: ${system}" >&2
   #echo "Temperature is: ${temp}" >&2
   #echo "Prompt is: ${prompt}" >&2

   curl -s http://localhost:9090/v1/chat/completions \
     -H "Content-Type: application/json" \
     -d "{ 
       \"model\": \"gemma-2-2b-it-q8_0\",
       \"messages\": [ 
         { \"role\": \"system\", \"content\": \"${system}\" },
         { \"role\": \"user\", \"content\": \"${prompt}\" }
       ], 
       \"temperature\": ${temp}, 
       \"max_tokens\": -1,
       \"stream\": false
   }" | jq '.choices[].message.content'
}

loc=$(curl -s "https://nominatim.openstreetmap.org/search?postalcode=${zip}&country=US&format=json")
lat=$(echo "scale=4; $(echo "${loc}" | jq -r '.[0] | "\(.lat)"') / 1 " | bc)
lon=$(echo "scale=4; $(echo "${loc}" | jq -r '.[0] | "\(.lon)"') / 1 " | bc)
station=$(curl -s "https://api.weather.gov/points/${lat},${lon}")
hourly=$(echo "${station}" | jq -r '.properties.forecastHourly')
city=$(echo "${station}" | jq -r '.properties.relativeLocation.properties.city')
state=$(echo "${station}" | jq -r '.properties.relativeLocation.properties.state')
rawhour=$(curl -s "${hourly}")
number=$(echo "${rawhour}" | jq -r '.properties.periods' | grep -B 2 $(date +"%Y-%m-%dT%H") | tail -n 3 | head -n 1 | sed -e 's/.* //g' -e 's/,.*//g')
forecast=$( echo "${rawhour}" | jq -r ".properties.periods | .[] | select(.number == ${number})" | tr -d '\n' | sed -e 's/"/\\"/g' )
curdate=$(date +"%a %b %d %Y %H:%M %p")

curllm "You are a meteorologist.  The Weather Station is LLM, Large Language Meteorology." "0.8" "We are in ${city}, ${state}. The current date is \`\`\`${curdate}\`\`\`.  The hourly forecast in JSON is \`\`\`${forecast}\`\`\`. Please provide a friendly and concise weather report based on the forecast. Focus only on the weather for each upcoming hour and keep the report engaging. Avoid making any predictions or comments about hours beyond the current one.  Write all numbers and abbeviations as words, for example instead of '10:51' is 'ten fifty-one'." | sed -e 's/\\n/ /g' -e 's/\*//g'
