# Run from the root 'clusive' directory

source ./env/scripts/activate
npm install
pip install -r requirements.txt
python -m nltk.downloader wordnet
grunt build
cd target
python manage.py migrate
python manage.py loaddata preferencesets tiptypes subjects
python manage.py importdir ../content
echo "Setup complete! Run python manage.py createsuperuser to create the super user and you're all done"
cd ..