# News Pulse

News Pulse reads the headlines of 115 English news sources, minute by minute, across ten topics, and shows how widely the news is covered (News Heat), how serious it is (Breadth), whether it is positive or negative (News Sentiment) and how fast it arrives (News Velocity), each compared with the same hours on comparable days.

By Dr. Jan Wüstenfeld · [@JanWues](https://x.com/JanWues) · [LinkedIn](https://www.linkedin.com/in/dr-jan-wuestenfeld/)

Page: https://janwuestenfeld.github.io/news/ . The page is updated about every 5 minutes (GitHub sometimes starts an update late or skips one); each page states the New York time its readings refer to. Each night (about 03:00 New York time) the finished day is added to the history page and the data files.

## Data
Daily and minute readings (no headlines): `data/` on the page. Licence: [CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Cite as: Wüstenfeld, J. (2026). News Pulse: daily and minute news readings, version 1 [Data set]. Retrieved <date> from https://janwuestenfeld.github.io/news/

Readings are derived automatically from public headlines and can contain labelling errors; past readings can be revised when the method or the label model changes. Nothing here is investment, financial or other professional advice. Headlines and articles remain the property of their publishers and are not part of the data files.

## This repository
`collector/`, `collect/`: the collection of new posts (public endpoints only). `pipeline/`: the code that computes the readings and builds the page. Workflows in `.github/workflows/`: collect (every 5 minutes), build (after each collection), nightly, raw-daily, pages.
