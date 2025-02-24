#!/bin/bash

movies=$(curl -s -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36' "https://www.rottentomatoes.com/browse/movies_at_home/sort:popular" | grep "@context")
let max=$(echo "${movies}" | jq | grep position | sed -e 's/.* //g' -e 's/\,.*//g' | tail -n 1)-1

for i in `seq 0 "${max}"` ; do
   name=$(echo "${movies}" | jq ".itemListElement.itemListElement.[${i}].name" | sed -e 's/"//g')
   critic_rating=$(echo "${movies}" | jq ".itemListElement.itemListElement.[${i}].aggregateRating.ratingValue" | sed -e 's/"//g')
   url=$(echo "${movies}" | jq ".itemListElement.itemListElement.[${i}].url" | sed -e 's/"//g')
   movie=$(curl -A 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36' -s "${url}")
   description=$(echo "${movie}" | grep -i "{\"audienceScore" | head -n 1 | jq .description | sed -e 's/^"//g' -e 's/"$//g')
   audience_rating=$(echo "${movie}" | grep -i "{\"audienceScore" | head -n 1 | jq .audienceScore.score | sed -e 's/"//g')
   audience_sentiment=$(echo "${movie}" | grep -i "{\"audienceScore" | head -n 1 | jq .audienceScore.sentiment | sed -e 's/"//g')
   critic_sentiment=$(echo "${movie}" | grep -i "{\"audienceScore" | head -n 1 | jq .criticsScore.sentiment | sed -e 's/"//g')
   director=$(echo "${movie}" | grep -i "@context" | sed -e 's/.*json">//g' -e 's/<\/script>.*//g' | jq .director.[].name | sed -e 's/"//g')
   mapfile -t actors < <(echo "${movie}" | grep -i "@context" | sed -e 's/.*json">//g' -e 's/<\/script>.*//g' | jq .actor.[].name | sed -e 's/"//g')
   actor_list=$(for actor in "${actors[@]}" ; do echo -n "${actor}, " ; done | sed -e 's/, $//g')
   echo "Film Title: ${name} | Critic Rating: ${critic_rating}%/100% and is ${critic_sentiment} | Audience Rating: ${audience_rating}%/100% and is ${audience_sentiment} | Director: ${director} | Actors: ${actor_list} | Description: ${description}"
done
