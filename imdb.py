from collections import OrderedDict
import requests
import bs4
import multiprocessing.dummy

class ImdbRatings(object):

    _ep_strainer = bs4.SoupStrainer("a", {"itemprop": "name"})
    _season_strainer = bs4.SoupStrainer("div", {"class": "seasons-and-year-nav"})
    _rating_strainer = bs4.SoupStrainer("span", {"itemprop": "ratingValue"})

    def __init__(self, series ="", parser="lxml", threads=1):
        self.series = series
        self.ratings = {}
        self.average = 0.0
        self.official_rating = ""
        self.episode_count = 0
        self.parser = parser
        self.threads = threads

        if self.parser == "html":
            self.parser += ".parser"


    def get_series_ratings(self, series):
        '''

        :param series: Title of series, uses imdb's find function to find series, grabs first result always
        :return: Dictionary of season dictionaries with episode ratings
        '''
        class SeriesError(Exception): pass
        try:
            with requests.get("http://imdb.com/find?q=" + series.replace(" ", "+")) as main_req: #parse find page for first result
                main_req.raise_for_status()
                main_soup = bs4.BeautifulSoup(main_req.content, self.parser, parse_only=bs4.SoupStrainer("td", {"class", "result_text"}))
                self.series = main_soup.a.string

            with requests.get("http://imdb.com" + main_soup.a["href"]) as sr_req: #parse official rating and year/seasons
                sr_req.raise_for_status()
                soup = bs4.BeautifulSoup(sr_req.content, self.parser, parse_only=self._rating_strainer)
                self.official_rating = soup.text
                sr_soup = bs4.BeautifulSoup(sr_req.content, self.parser, parse_only=self._season_strainer)

        except Exception as e: #print exception to parsing
            raise SeriesError("Error in parsing series page")

        if len(main_soup) == 0: #if main soup is empty then there find failed
            raise SeriesError("Error: No seasons on {} series page".format(self.series))

        sn_links = []
        for tag in sr_soup.find_all("a"): #get all season links from season/year soup
            if tag.has_attr("href") and tag["href"].split("_")[-2] == "sn":
                sn_links.append("http://imdb.com" + tag["href"])

        if len(sn_links) == 0:
           raise SeriesError("Error: No seasons found (is the first result a show?)")

        if sn_links[-1][-1] == "r": # if there are too many seasons to display on main page and See all... is given get links from there
            max_sn = int(sn_links[0][-2:])
            numName = sn_links[0].split("/")[-2]
            sn_links.clear()
            for i in range(max_sn,0,-1):
                sn_links.append("http://imdb.com/title/{}/episodes?season={}".format(numName,i))

        pool = multiprocessing.dummy.Pool(self.threads) #thread pool for getting episode ratings out of season links
        tmpratings = pool.map(self.get_season_ratings, sn_links)

        self.ratings = {x+1:y for x,y in enumerate(tmpratings[::-1])} #convert ratings to proper dict

        for i,x in enumerate(sn_links[::-1]):
            if x[-2:] == "-1":
                self.ratings[-1] = tmpratings[-1]
                self.ratings.pop(i+1)
                break

        return sorted(self.ratings)


    def get_season_ratings(self, url):
        '''

        :param url: URL of season page to parse for episodes, calls get_ep_rating on all parsed episode links using thread pool
        :return:
        '''
        class SeasonError(Exception): pass
        currLst = []
        try:
            with requests.get(url) as sn_req: #parse for episodes
                sn_req.raise_for_status()
                sn_soup = bs4.BeautifulSoup(sn_req.content, self.parser, parse_only=self._ep_strainer)

        except Exception as e:
            raise SeasonError("Error in parsing season page")

        if len(sn_soup) == 0:
            raise SeasonError("Error: No episodes found in season page")

        for ep in sn_soup.find_all('a'):  # find only episode links append proper link to list
            if ep.has_attr("href"):
                currLst.append("http://imdb.com" + ep["href"])

        pool = multiprocessing.dummy.Pool(self.threads)
        tmp = pool.map(self.get_ep_rating, currLst) #get each episode rating using threads
        currLst = {x+1:y for x,y in enumerate(tmp)} # convert to proper dict

        return currLst


    def get_ep_rating(self, url):
        try:
            with requests.get(url) as file:
                file.raise_for_status()
                soup = bs4.BeautifulSoup(file.content,self.parser, parse_only=self._rating_strainer)
            if soup.span != None: # if soup is not empty then there is a rating, add to count and return score
                self.episode_count += 1
                return soup.text
            else: # if it is None then reutrn N/A as score and dont add to count
                return "N/A"
        except:
            class EpError(Exception): pass
            raise EpError("Error in parsing episode page")


    def get_ratings(self):
        '''
        :return: Returns string of formatted episodes and ratings
        '''
        if self.series == "":
            return "Error no series"

        outStr = ""
        unknownChk = False

        if len(self.ratings) == 0:
            self.get_series_ratings(self.series)

        outStr+= self.series + "\n-----------------------------"

        for sn in sorted(self.ratings.keys()):
            if sn == -1:
                outStr += "\nSeason Unknown: \n"
                unknownChk = True
            else:
                if unknownChk:
                    outStr += "\nSeason {}:\n".format(str(sn-1))
                else:
                    outStr += "\nSeason {}:\n".format(str(sn))

            for i in sorted(self.ratings[sn].keys()):
                outStr += "Episode {0}: {1}  ".format(str(i), self.ratings[sn][i])
            outStr += "\n\n"

        if self.average == 0.0:
            self.get_ep_average()

        outStr += "Series rating: {}".format(self.official_rating)
        outStr += "\nEpisode average rating: %0.1f" % self.average
        outStr += "\n\nSeries rating is %0.1f points above episode average" % (float(self.official_rating)- self.average)

        return outStr

    def get_ep_average(self):
        try:
            for sn in self.ratings:
                for i in self.ratings[sn]:
                    if self.ratings[sn][i] != "N/A":
                        self.average += float(self.ratings[sn][i])

            self.average /= self.episode_count

        except Exception as e:
            class AvError(Exception): pass
            raise AvError("Error in calculating average of episode")


if __name__ == "__main__":
    imdbx = ImdbRatings("nathan for you", parser="lxml", threads=16)
    print(imdbx.get_ratings())