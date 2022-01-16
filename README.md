## PlanetTerp

<https://planetterp.com/>

PlanetTerp is a website designed to help students at the University of Maryland — College Park (UMD) make informed decisions. We have a professor review system, grades for each course and professor, and tools to provide information related to UMD.

This is the second version of PlanetTerp. The first was written in [webpy](https://github.com/webpy/webpy), and was closed source. It was rewritten in [django](https://github.com/django/django) at the beginning of 2022, which is the version you see here.

All contributions are welcome, whether that be opening an issue with a bug or feature request, or opening a pull requets. See below for how to set up PlanetTerp locally.

### Setup

PlanetTerp is developed against python 3.9. It's likely that 3.7+ will work, but we only officially support 3.9+.

To set up locally:

(TODO test this on a fresh install)

```bash
git clone https://github.com/planetterp/planetterp
cd planetterp
pip install -r requirements.txt
python manage.py migrate
# we provide some initial data (reviews, courses, professors,
# grades, users, etc) for developers. If you prefer to start from
# a completely blank database, skip this step.
python manage.py loaddata initial
```

Now simply run the following to start the server:

```bash
python manage.py runserver
```
