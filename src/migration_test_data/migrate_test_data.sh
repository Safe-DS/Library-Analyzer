#!/bin/bash

cd ./src/migration_test_data/api/apiv2/ || exit
mv library_apiv2 library_api
cd ../../..
poetry run python -m library_analyzer api -s ./src/migration_test_data/api/apiv2/library_api -p library_api -o ./src/migration_test_data/api/apiv2
poetry run python -m library_analyzer migrate -a1 ./src/migration_test_data/api/apiv1/library_api__api.json -a2 ./src/migration_test_data/api/apiv2/library_api__api.json -a ./src/migration_test_data/api/apiv1/annotations_apiv1.json -o ./migration_test_data
cd ./src/migration_test_data/api/apiv2/ || exit
mv library_api library_apiv2
