News Pulse, daily readings, 1 Aug 2025 to 2026-11-05. Dr. Jan Wüstenfeld (@JanWues). Cite as: News Pulse, Jan Wüstenfeld.
All readings are at the close of the day (24:00 New York time). A 0-100 reading compares the day with comparable days (same kind
of day, weekday or weekend, in the previous 26 weeks): 80 means higher than on 80 of 100 of them; 50 is a typical day. Empty =
not enough comparable days or sources. Headlines and per-source data are not included.

news_pulse_daily.csv (one row per day)
  news_heat                 how much more widely than usual the day's top topic is covered (0-100): the topic furthest above
                            its usual number of sources carrying it
  news_heat_leading_topic   that topic (the day's top topic)
  breadth                   how many sources report more serious news than they usually do (0-100); _sources_more_serious of _sources_read
  news_sentiment            balance of positive and negative news across topics, against comparable days (0-100; low = more negative)
  confluence                negative / positive shock day (news_heat and breadth both 75+, sentiment 25 or below / 75 or above),
                            shock day, mixed direction (both 75+, sentiment in between); busy, ordinary (heat 75+, breadth below 50);
                            serious news, few sources (heat below 50, breadth 75+); quiet (both below 50); otherwise mixed
  news_velocity             how fast notable stories arrive so far in the day (0-100); _times_usual = stories / usual stories
  focus_topic, focus_share, focus_usual_share   the topic with the largest share of notable stories, its share and usual share
  consensus_geopolitics     how alike the sources rate Geopolitics at 14:00 (0-100; high = more agreement than usual)
  consensus_us_politics     the same for US politics at the close
  shock_share               share of notable stories at the top grade (0.9 or more); _rank against comparable days (0-100)

news_pulse_topics_daily.csv (one row per day and topic)
  news_heat                 sources carrying notable news on the topic, against comparable days (0-100);
                            sources_carrying, sources_usual = today's count and the usual count
  negative_news, positive_news, sentiment   sources carrying negative / positive news, and their balance (0-100); only for
                            topics with a direction reading
  breadth                   sources whose news on the topic is more serious than usual for them (0-100), with the counts
  confluence                negative / positive shock, or shock, mixed direction, when news_heat and breadth are both 75+

Method: methods page. Revisions: readings are recomputed when the method or the label model changes; each release is versioned.

HOW TO CITE
  Wüstenfeld, J. (2026). News Pulse: daily news readings, version 1 [Data set]. Retrieved <date> from
  https://janwuestenfeld.github.io/news/

TERMS OF USE
  Licence: Creative Commons Attribution 4.0 International (CC BY 4.0), https://creativecommons.org/licenses/by/4.0/.
  You may share and adapt the data for any purpose, provided you credit the source as above and indicate if you changed it.
  The data are provided as is, for information and research, without warranty of any kind as to accuracy, completeness or
  timeliness. They are derived automatically from public headlines and can contain labelling errors; past readings can be
  revised. Nothing here is investment, financial or other professional advice. The author accepts no liability for any use
  of the data. The licence covers the readings only, not the headlines they are derived from.
