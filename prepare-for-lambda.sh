cd ./app/services/

shopt -s nullglob

for dir in */; do
    if [ -d "$dir" ]; then
      mkdir -p "$dir/apps"
        for file in "$dir"/*; do
          if [ ! -d "$file" ]; then
            mv -v "$file" "$dir/apps"
          fi
        done
    fi
done
