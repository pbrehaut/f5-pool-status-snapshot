#!/bin/bash

# Create parsed directory if it doesn't exist
mkdir -p parsed

# Process each snapshot file separately and save results
for file in pool_snapshot_*.txt; do
    if [ -f "$file" ]; then
        output_file="parsed/${file%.txt}_parsed.txt"
        awk 'BEGIN { RS="\n}\n" } /ltm pool / { 
            match($0, /ltm pool ([^ ]+)/, pool); 
            match($0, /status\.availability-state ([^ \n]+)/, status); 
            print pool[1], status[1] 
        }' "$file" > "$output_file"
        echo "Parsed $file -> $output_file"
    fi
done

# Get list of parsed files
parsed_files=($(ls -t parsed/pool_snapshot_*_parsed.txt 2>/dev/null))

if [ ${#parsed_files[@]} -lt 2 ]; then
    echo "Need at least 2 parsed files to compare"
    exit 1
fi

echo
echo "Available parsed files:"
for i in "${!parsed_files[@]}"; do
    echo "$((i+1)). $(basename "${parsed_files[$i]}")"
done

echo
read -p "Select first file (1-${#parsed_files[@]}): " choice1
read -p "Select second file (1-${#parsed_files[@]}): " choice2

# Validate choices
if [[ ! "$choice1" =~ ^[0-9]+$ ]] || [ "$choice1" -lt 1 ] || [ "$choice1" -gt ${#parsed_files[@]} ]; then
    echo "Invalid first choice. Please select a number between 1 and ${#parsed_files[@]}"
    exit 1
fi

if [[ ! "$choice2" =~ ^[0-9]+$ ]] || [ "$choice2" -lt 1 ] || [ "$choice2" -gt ${#parsed_files[@]} ]; then
    echo "Invalid second choice. Please select a number between 1 and ${#parsed_files[@]}"
    exit 1
fi

# Convert to array indices (subtract 1)
file1="${parsed_files[$((choice1-1))]}"
file2="${parsed_files[$((choice2-1))]}"

echo
echo "Running diff between $(basename "$file1") and $(basename "$file2"):"
echo "=================================================="
diff "$file1" "$file2"
