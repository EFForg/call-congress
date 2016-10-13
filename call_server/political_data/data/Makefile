all: legislators-current.yaml us_states.csv

clean:
	rm -rf -- *.csv *.yaml

legislators-current.yaml :
	curl -k "https://raw.githubusercontent.com/unitedstates/congress-legislators/master/legislators-current.yaml" -o "legislators-current.yaml"

us_states.csv:
	curl -k "https://raw.githubusercontent.com/spacedogXYZ/us_governors_contact/master/data.csv" -o "us_states.csv"
