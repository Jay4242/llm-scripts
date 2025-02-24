#!/bin/bash

#Set overall temperature. (Where not explicitly set, ie. 0.0)
temp="0.7"

#Set Plex API Key
api=""             #Enter your Plex API Key Here.

#Set Current Date
curdate=$(date +"%a %b %d %Y %H:%M %p")

#Create Temp Directory
temp_dir=$(mktemp -d -p /dev/shm llm-plex.XXXXXX) || exit 1

#Fetch the existing movie Genres from Plex.
genres=$(curl -s "http://plex.lan/library/sections/1/genre?X-Plex-Token=${api}")
mapfile -t genres < <(echo "${genres}" | xmlstarlet sel -t -m "//Directory" -v "concat(@key, ',' , @title)" -n )

#Echo those genres into a file.
for genre in "${genres[@]}" ; do
   echo "${genre}" | cut -d',' -f2
done | shuf > "${temp_dir}/llm-plex.txt"

#Have the bot choose a genre.
genrec=$(llm-python-file.py "${temp_dir}/llm-plex.txt" "You are a movie expert. The current date is ${curdate}" "The following are the available movie genres we can select from:" "What genre should we pick?  Output your selection in JSON format and do not give any explanation." "${temp}" | sed -e 's/\\n/\n/g' | grep -v -e '```' | jq -r '.genre')

#Filter against the actual genres so that we can match using the API ID.
genre=$(for genre in "${genres[@]}" ; do
echo "${genre}" | grep -i "${genrec}" | cut -d',' -f1
done)

genre_name=$(for genre in "${genres[@]}" ; do
echo "${genre}" | grep -i "${genrec}" | cut -d',' -f2
done)

#Output the Genre Movie Suggestion title.
echo "------------${genre_name} Suggestion------------"

#Fetch the movies of that genre in the user's Plex.
movies=$(curl -s "http://plex.lan/library/sections/1/genre/${genre}?X-Plex-Token=${api}")

#Filter the information into a text file.
echo "${movies}" | xmlstarlet sel -t -m "//Video" -v "concat('Title: \`', @title)" -v "concat('\` RottenTomatoes Critic Rating: \`', @rating)" -v "concat('\` Audience Rating: \`', @audienceRating)" -v "concat('\` Year: \`', @year)" -v "concat('\` Summary: \`', @summary)" -v "concat('\` Director: \`', Director/@tag)" -v "concat('\` Genre: \`', Genre/@tag)" -v "concat('\`', '' )" -n | shuf > "${temp_dir}/llm-plex.txt"

#Have the LLM pick a movie.
llm-python-file.py "${temp_dir}/llm-plex.txt" "You are a movie expert. The current date is ${curdate}" "The following is the list of \`${genrec}\` movies that are available to play:" "Based on that list what movie should I watch next? Output only your top selection based on your expertise." "${temp}"


#Output the Unwatched Movie Suggestion title.
echo "------------Unwatched Suggestion------------"

#Fetch the Unwatched movies from the user's Plex.
movies=$(curl -s "http://plex.lan/library/sections/1/unwatched?X-Plex-Token=${api}" )

#Filter the information into a text file.
echo "${movies}" | xmlstarlet sel -t -m "//Video" -v "concat('Title: \`', @title)" -v "concat('\` RottenTomatoes Critic Rating: \`', @rating)" -v "concat('\` Audience Rating: \`', @audienceRating)" -v "concat('\` Year: \`', @year)" -v "concat('\` Summary: \`', @summary)" -v "concat('\` Director: \`', Director/@tag)" -v "concat('\` Genre: \`', Genre/@tag)" -v "concat('\`', '' )" -n | shuf > "${temp_dir}/llm-plex.txt"

#Have the LLM pick a movie.
llm-python-file.py "${temp_dir}/llm-plex.txt" "You are a movie expert. The current date is ${curdate}" "The following is the list of movies that are available to watch:" "Based on that list what movie should I watch next? Output only your top selection based on your expertise." "${temp}"

#Output the RottenTomatoes Movie Suggestion title.
echo "------------RottenTomatoes Suggestion------------"

#Fetch All the user's movies from their Plex.
movies=$(curl -s "http://plex.lan/library/sections/1/all?X-Plex-Token=${api}" )

#Filter the movie information into a text file.
echo "${movies}" | xmlstarlet sel -t -m "//Video" -v "concat('Title: \`', @title)" -v "concat('\` RottenTomatoes Critic Rating: \`', @rating)" -v "concat('\` Audience Rating: \`', @audienceRating)" -v "concat('\` Year: \`', @year)" -v "concat('\` Summary: \`', @summary)" -v "concat('\` Director: \`', Director/@tag)" -v "concat('\` Genre: \`', Genre/@tag)" -v "concat('\`', '' )" -n | shuf > "${temp_dir}/llm-plex.txt"

#Run the RottonTomatoes scraper and save it to a text file.
llm-rottentomatoes.bash > "${temp_dir}/rottentomatoes.txt" 2>/dev/null

#Feed the user's complete movie list & RottenTomatoes scraped information to suggest a movie.
llm-python-file-2.py "${temp_dir}/llm-plex.txt" "${temp_dir}/rottentomatoes.txt" "You are a movie expert. The current date is ${curdate}" "The following is the user's current movie collection:" "The following are the current Movie Releases:" "Of the current movie releases, which ones fit the user's movie tastes the most and why?" "0.7"
