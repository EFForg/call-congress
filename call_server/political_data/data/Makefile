all: us_states.csv

clean:
	rm -rf -- *.csv

us_states.csv:
	curl -k "https://raw.githubusercontent.com/spacedogXYZ/us_governors_contact/master/data.csv" -o "us_states.csv"
