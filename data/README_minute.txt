News Pulse, minute-by-minute readings, 2025-08 to 2026-11 (New York time). Dr. Jan Wüstenfeld (@JanWues).

The same readings as the daily files and the front page, at every minute of the day. The row for minute HH:MM uses the
headlines posted before HH:MM New York time (00:01 = the first minute, 24:00 = the close). Headlines and per-source data
are not included.

FILES (one pair per month, CSV compressed with gzip; most programs open them directly)
  news_pulse_minute_YYYY-MM.csv.gz         one row per day and minute: the readings for all topics together
  news_pulse_minute_topics_YYYY-MM.csv.gz  one row per day, minute and topic
  The current month grows during the day: each update of the page adds the minutes since the previous update; after
  the close the day's rows are replaced by the final ones.
  The final rows are recomputed in the night from the whole finished day (for example, whether a source posted enough
  that day to count in the readings is decided on all its headlines of the day), so a minute row can differ from what the
  page showed live at that minute. On 5 Nov 2026, 00:01 to 12:40 (760 minutes), News Velocity differed on 754 minutes (by
  up to 24 points), Consensus on Geopolitics on 396 (up to 38), the Severe News Share rank on 328 (up to 8), News
  Sentiment of the last 3 hours on 741 (up to 5) and News Heat on 5 (up to 1); Breadth, News Sentiment and the flags
  were equal.

COMPARABLE DAYS
  A 0-100 reading compares the day at that minute with the comparable days at the same minute: 80 means higher than on
  80 of 100 of them; 50 is a typical value. Ties count half. Comparable days are earlier days of the same kind (weekday,
  or Saturday and Sunday):
    News Heat (all readings and topics), negative and positive news, News Velocity, Focus, Severe News Share, flags: the
      previous 182 days.
    Breadth, Consensus, the usual ranges on the page: the previous 182 days.
    News Sentiment: the previous 365 days.
    A US weekday market holiday is read against the working days and against the Saturdays and Sundays, and the two
    results are averaged; holidays are never comparable days for other days.
  Empty = not enough comparable days or sources yet at that minute (early in the day this is common).

news_pulse_minute_YYYY-MM.csv.gz
  date, clock, day_type
  news_heat                 how much more widely than usual the top topic is covered so far (0-100)
  news_heat_leading_topic   that topic
  breadth                   how many sources report more serious news so far than they usually do by that minute (0-100);
                            breadth_sources_more_serious of breadth_sources_read
  news_sentiment            balance of positive and negative news so far (0-100; low = more negative); _last_3h: the last 3 hours
  confluence                as in the daily file, from news_heat, breadth and news_sentiment at that minute
  news_velocity             how fast notable stories arrive so far (0-100); _times_usual = median over sources of (the source's
                            stories / its usual stories by that minute)
  focus_topic, focus_share, focus_usual_share   per source the largest topic's share of its notable stories so far, averaged
                            over sources; the topic most often largest; usual share = median on comparable days
  consensus_geopolitics, consensus_us_politics  how alike the sources rate the topic so far (0-100; high = more agreement
                            than usual). The daily file gives Geopolitics at 14:00 and US politics at the close.
  severe_news_share         per source the share of its notable stories at the top grade (0.9 or more), averaged over sources;
                            _rank against comparable days (0-100)
  topics_unusually_negative, topics_unusually_positive   number of topics with sources carrying negative (positive) news
                            at 90 or more, and _names
  flags_negative, flags_positive   topics with a flag at that minute ("All topics" when two or more topics are flagged on
                            the same side). A flag: more sources with news of that side in the last 3 hours than at that minute
                            on every comparable day, at least 5 such stories from at least 3 sources, and the topic's News Heat
                            75 or more; raised after 15 minutes, kept at least 30, ended after 30 minutes without the condition.

news_pulse_minute_topics_YYYY-MM.csv.gz
  date, clock, topic
  news_heat                 sources carrying notable news on the topic so far, against comparable days (0-100);
                            sources_carrying, sources_usual = the count so far and the usual count by that minute
  negative_news, positive_news   sources carrying negative / positive news on the topic (0-100), with _sources (the count)
  sentiment                 balance of positive and negative news on the topic (0-100)
  breadth                   sources whose news on the topic is more serious than usual for them (0-100), with the counts
  flag_negative, flag_positive   1 while the topic has a flag of that side

Method: methods page. Revisions: readings are recomputed when the method or the label model changes; each release is versioned.

HOW TO CITE
  Wüstenfeld, J. (2026). News Pulse: daily and minute news readings, version 1 [Data set]. Retrieved <date> from https://janwuestenfeld.github.io/news/

TERMS OF USE
  Licence: Creative Commons Attribution 4.0 International (CC BY 4.0), https://creativecommons.org/licenses/by/4.0/.
  You may share and adapt the data for any purpose, provided you credit the source as above and indicate if you changed it.
  The data are provided as is, for information and research, without warranty of any kind as to accuracy, completeness or
  timeliness. They are derived automatically from public headlines and can contain labelling errors; past readings can be
  revised. Nothing here is investment, financial or other professional advice. The author accepts no liability for any use
  of the data. The licence covers the readings only, not the headlines they are derived from.
