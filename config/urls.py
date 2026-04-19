# config/urls.py
#
# Stores all provider URLs to fetch data from.
# To add a new provider: add a new key with a list of URLs.
# The fetcher will visit every URL in the list and combine the content.

PROVIDERS = {
    "Miami Valley Hospital North": [
        "https://www.healthgrades.com/hospital/miami-valley-hospital-north-hg7524----",
        "https://www.premierhealth.com/locations/hospitals/miami-valley-hospital-north----"
    ],
    "Soin Medical Center": [
       "https://www.healthgrades.com/hospital/soin-medical-center-a7c200",
       "https://ketteringhealth.org/locations/soin-medical-center-kettering-health-mc005/"
    ],
    "Dayton Childrens Hospital": [
       "https://www.healthgrades.com/hospital/dayton-childrens-hospital-70717b",
       "https://childrensdayton.org/locations/main-campus/",
       "https://childrensdayton.org/locations/",
       "https://childrensdayton.org/about-us/contact-us/"
    ],
    "Ohio Valley Surgical Hospital":[
        "https://www.ovsurgical.com/",
        "https://www.ovsurgical.com/our-locations/ohio-valley-surgical-hospital/",
        "https://www.healthgrades.com/hospital/ohio-valley-surgical-hospital-d9adbc",
        "https://www.ovsurgical.com/our-physicians/",
        "https://www.ovsurgical.com/contact-us/",
        "https://www.ovsurgical.com/patients-visitors/billing-insurance/"
    ],
    "Centerpoint Health": [
        "https://www.centerpointhealth.org/",
        "https://www.centerpointhealth.org/clinicians/",
        "https://www.centerpointhealth.org/clinicians/adult-medical-providers/",
        "https://www.centerpointhealth.org/clinicians/integrated-behavioral-health-providers/",
        "https://www.centerpointhealth.org/clinicians/nutrition-services/",
        "https://www.centerpointhealth.org/clinicians/pediatric-providers/",
        "https://www.centerpointhealth.org/clinicians/womens-health-and-ob-providers/",
        "https://www.centerpointhealth.org/locations/",
        "https://www.centerpointhealth.org/contact-us/",
    ]
}

NPPES_URL = "https://npiregistry.cms.hhs.gov/api/"
