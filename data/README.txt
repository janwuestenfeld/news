News Pulse, daily readings, 1 Aug 2025 to 2026-11-05, from the headlines of 115 sources. Dr. Jan Wüstenfeld (@JanWues).
All readings are at the close of the day (24:00 New York time; Consensus on Geopolitics at 14:00): the same values as the
front page and the 24:00 rows of the minute files. A 0-100 reading compares the day with comparable days at the same time,
earlier days of the same kind (weekday, or Saturday and Sunday): 80 means higher than on 80 of 100 of them; 50 is a typical day.
Comparable days: the previous 182 days (News Sentiment: the previous 365 days). A US weekday market holiday is read against
the working days and against the Saturdays and Sundays, and the two results are averaged; holidays are never comparable days.
Empty = not enough comparable days or sources. Headlines and per-source data are not included.

news_pulse_daily.csv (one row per day)
  news_heat                 how much more widely than usual the day's top topic is covered (0-100): the topic furthest above
                            its usual number of sources carrying it
  news_heat_leading_topic   that topic (the day's top topic)
  breadth                   how many sources report more serious news than they usually do (0-100); _sources_more_serious of _sources_read
                            Breadth has no value on 83 days at the start of the history (1 Aug 2025 to 20 Dec 2025): a
                            source needs at least 20 comparable days with stories, and the day's share of sources needs
                            at least 20 comparable days with a share. The first day with a value is 29 Sep 2025; on
                            Saturdays and Sundays, which have fewer comparable days, values start later (last day
                            without one: 20 Dec 2025).
  news_sentiment            balance of positive and negative news across topics, against comparable days (0-100; low = more negative)
  confluence                widely covered and serious (news_heat and breadth both 75+), with ", negative" / ", positive" when
                            news_sentiment is 25 or below / 75 or above; busy, ordinary (heat 75+, breadth below 50);
                            serious news, few sources (heat below 50, breadth 75+); quiet (both below 50); otherwise mixed
  news_velocity             how fast notable stories arrive so far in the day (0-100); _times_usual = median over sources of
                            (the source's stories / its usual stories)
  focus_topic, focus_share, focus_usual_share   per source the largest topic's share of its notable stories, averaged over
                            sources; the topic most often largest; usual share = median on comparable days
  consensus_geopolitics     how alike the sources rate Geopolitics at 14:00 (0-100; high = more agreement than usual)
  consensus_us_politics     the same for US politics at the close
  severe_news_share         per source the share of its notable stories at the top grade (0.9 or more), averaged over sources;
                            _rank against comparable days (0-100)

news_pulse_topics_daily.csv (one row per day and topic)
  news_heat                 sources carrying notable news on the topic, against comparable days (0-100);
                            sources_carrying, sources_usual = today's count and the usual count
  negative_news, positive_news   sources carrying negative / positive news on the topic, against comparable days (0-100)
  sentiment                 balance of positive and negative news on the topic (0-100; low = more negative)
  breadth                   sources whose news on the topic is more serious than usual for them (0-100), with the counts

Method: methods page. Revisions: readings are recomputed when the method or the label model changes.

HOW TO CITE
  Wüstenfeld, J. (2026). News Pulse: daily and minute news readings, version 1 [Data set]. Retrieved <date> from https://janwuestenfeld.github.io/news/

TERMS OF USE
  Licence: Creative Commons Attribution 4.0 International (CC BY 4.0), https://creativecommons.org/licenses/by/4.0/.
  You may share and adapt the data for any purpose, provided you credit the source as above and indicate if you changed it.
  The data are provided as is, for information and research, without warranty of any kind as to accuracy, completeness or
  timeliness. They are derived automatically from public headlines and can contain labelling errors; past readings can be
  revised. Nothing here is investment, financial or other professional advice. The author accepts no liability for any use
  of the data. The licence covers the readings only, not the headlines they are derived from.
