# Threads draft — DRAFT, do not publish without approval

Half the internet runs on one person.

I measured npm, the registry every JavaScript app installs from. 53% of downloads in the top 1,000 packages flow through packages with exactly one maintainer. The median solo package gets downloaded 117 million times a week.

And a quarter of those downloads flow through packages nobody has touched in 2+ years. ms, the little time-parsing library in basically everything, was last published in December 2020. It still gets 727 million downloads a week.

Most of these packages aren't broken. They're finished. That's the scary part. Nobody is watching them, and a compromised publish would ship silently into hundreds of millions of installs.

npm is the biggest marketplace in software, and its supply side is unpaid individuals. The cheapest insurance in tech might be paying the person who maintains the 20-line package your whole stack stands on.

Full census: https://github.com/mzhou-ds/passion-projects/tree/main/2026-11-28/the-one-person-internet
