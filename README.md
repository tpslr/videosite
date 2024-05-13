# videosite
Databases and web programming uni course project.

Users can quickly upload a video and share the link with others.

A test page should be running at [videosite.topias.xyz](https://videosite.topias.xyz), for installation instructions, see [installation.md](installation.md).


# Videonjakosivu

Sivulle voi nopeasti ladata videon, ja jakaa videon linkin jonnekkin, jolla muut voivat katsoa sen
Sivu on saatavilla osoitteessa [videosite.topias.xyz](https://videosite.topias.xyz)

Asennusohjeet paikallista testausta varten löytyvät tiedostosta [installation.md](installation.md)

## Ominaisuudet
* Käyttäjä voi ladata sivulle videon
* Videot ovat katsottavissa pelkällä linkillä ilman kirjautumista
* Käyttäjä voi nähdä sivulla listan itse lataamistaan videoista, ja hallita niitä
* Sivua voi käyttää kirjautuneena käyttäjänä tai ilman kirjautumista, jolloin sivu kuitenkin yrittää muistaa käyttäjän jollain token-arvolla
* Anonyymit eri kirjautumattomat käyttäjät ja niiden videot poistetaan automaattisesti jonkin ajan kuluttua
* Anonyymi käyttäjä voi luoda tilin ja kirjautua sisään, jolloin käyttäjästä tulee pysyvä
* Kirjautuneet käyttäjät voivat jättää videoihin kommentteja ja tykkäyksiä
* Ylläpitäjät voivat nähdä listan kaikista videoista ja poistaa muiden käyttäjien videoita
* Käyttäjät voivat reporttaa videon ja ylläpitäjät voivat lukea nämä reportit ja tarkastaa videon


## Toimivat ominaisuudet
* Käyttäjä voi ladata sivulle videon
* Videot katsottavissa
* Lista videoista näkyy
* Sivua voi käyttää kirjautumatta
* Käyttäjän luonti
* Kirjautuminen
* Yksityiset videot
* Videoiden poistaminen
* Kommentit


## Puuttuvat ominaisuudet
* Tykkäykset
* Ylläpitäjät
* Videoiden reportit


## Ongelmat
* käyttöliittymä näyttää hirveältä vaalealla teemalla
* jotkin uusimmista toiminnoista eivät anna mitään visuaalista palautetta, että mitään olisi tapahtumassa (videon asettaminen yksityiseksi, kommentin lähettäminen)
* videon katsomisen UI on surkea
