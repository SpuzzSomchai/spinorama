echo "Starting Generation"
export PYTHONPATH=src:.
rm -fr docs
rm -f cache.*.h5
mkdir docs docs/assets docs/pictures
# generates smaller pictures
./update_pictures.sh
# generates all graphs per speaker
python3 ./generate_graphs.py
# save some space and generates jpg from png
./update_pictures.sh
# all metadata (computed)
python3 ./generate_meta.py
python3 ./generate_compare.py
# some stats for all speakers
python3 ./generate_stats.py
# static website generation
python3 ./generate_html.py
echo "Done"
