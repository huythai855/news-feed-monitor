"""
Name: Nguyen Huy Thai
Collaborators: No one
Time: ~ 5hrs
"""

import feedparser
import string
import time
import threading
from project_util import translate_html
from mtTkinter import *
from datetime import datetime
import pytz


# -----------------------------------------------------------------------

# ======================
# Code for retrieving and parsing
# Google and Yahoo News feeds
# Do not change this code
# ======================


def process(url):
    """
    Fetches news items from the rss url and parses them.
    Returns a list of NewsStory-s.
    """
    feed = feedparser.parse(url)
    entries = feed.entries
    ret = []
    for entry in entries:
        guid = entry.guid
        title = translate_html(entry.title)
        link = entry.link
        description = translate_html(entry.description)
        pubdate = translate_html(entry.published)

        try:
            pubdate = datetime.strptime(pubdate, "%a, %d %b %Y %H:%M:%S %Z")
            pubdate.replace(tzinfo=pytz.timezone("GMT"))
        except ValueError:
            pubdate = datetime.strptime(pubdate, "%a, %d %b %Y %H:%M:%S %z")

        newsStory = NewsStory(guid, title, description, link, pubdate)
        ret.append(newsStory)
    return ret


# ======================
# Data structure design
# ======================


class NewsStory:
    """
    A news story or article parsed from the feeds (Google/Yahoo/etc).
    """
    def __init__(self, guid, title, description, link, pubdate):
        self.guid = guid
        self.title = title
        self.description = description
        self.link = link
        self.pubdate = pubdate

    def get_guid(self):
        return self.guid

    def get_title(self):
        return self.title

    def get_description(self):
        return self.description

    def get_link(self):
        return self.link

    def get_pubdate(self):
        return self.pubdate


# ======================
# Triggers
# ======================


class Trigger(object):
    def evaluate(self, story):
        """
        Returns True if an alert should be generated
        for the given news item, or False otherwise.
        """
        raise NotImplementedError


# PHRASE TRIGGERS
class PhraseTrigger(Trigger):
    def __init__(self, phrase):
        # Lowercase the phrase.
        phrase = phrase.lower()
        self.phrase = phrase

    def is_phrase_in(self, text):
        """
        Returns True if each word in the phrase is present in its entirety
        and appears consecutively in the text, or False otherwise.
        """
        # Lowercase text string.
        text = text.lower()
        # Replace each punctuation in the text with a whitespace.
        for char in string.punctuation:
            text = text.replace(char, ' ')
        # Check if each word in the phrase appears consecutively in the text.
        is_phrase_in = False
        text_words = text.split()
        phrase_words = self.phrase.split()
        for i in range(len(text_words) - len(phrase_words) + 1):
            if text_words[i:i+len(phrase_words)] == phrase_words:
                is_phrase_in = True
                break
        return is_phrase_in


class TitleTrigger(PhraseTrigger):
    """
    The trigger that fires when a story's title contains a given phrase.
    """
    def __init__(self, phrase):
        super().__init__(phrase)

    def evaluate(self, story: NewsStory):
        return self.is_phrase_in(story.title)


class DescriptionTrigger(PhraseTrigger):
    """
    The trigger that fires when a story's description contains a given phrase.
    """
    def __init__(self, phrase):
        super().__init__(phrase)

    def evaluate(self, story: NewsStory):
        return self.is_phrase_in(story.description)


# TIME TRIGGERS
class TimeTrigger(Trigger):
    def __init__(self, time_in_est):
        # convert the given time string to the corresponding datetime format.
        date_object = datetime.strptime(time_in_est, "%d %b %Y %H:%M:%S")
        # add the offset for the story's pubdate.
        date_object = date_object.replace(tzinfo=pytz.timezone("EST"))
        self.date_object = date_object


class BeforeTrigger(TimeTrigger):
    """
    The trigger that fires when a story is published strictly before the trigger’s time.
    """
    def evaluate(self, story: NewsStory):
        # add the offset for the story's pubdate.
        pubdate_with_offset = story.pubdate.replace(tzinfo=pytz.timezone("EST"))
        return pubdate_with_offset < self.date_object


class AfterTrigger(TimeTrigger):
    """
    The trigger that fires when a story is published strictly after the trigger’s time.
    """
    def evaluate(self, story: NewsStory):
        # add the offset for the story's pubdate.
        pubdate_with_offset = story.pubdate.replace(tzinfo=pytz.timezone("EST"))
        return pubdate_with_offset > self.date_object


# COMPOSITE TRIGGERS
class NotTrigger:
    """
    The trigger that fires when a story does not fire another specific trigger.
    """
    def __init__(self, trigger: Trigger):
        self.trigger = trigger

    def evaluate(self, story):
        return not self.trigger.evaluate(story)


class AndTrigger(Trigger):
    """
    The trigger that takes two triggers and fires only if both of these triggers fire on a story.
    """
    def __init__(self, first_trigger: Trigger, second_trigger: Trigger):
        self.first_trigger = first_trigger
        self.second_trigger = second_trigger

    def evaluate(self, story: NewsStory):
        return self.first_trigger.evaluate(story) and self.second_trigger.evaluate(story)


class OrTrigger(Trigger):
    """
    The trigger that takes two triggers and fires
    if either one (or both) of these triggers fire on a story.
    """
    def __init__(self, first_trigger: Trigger, second_trigger: Trigger):
        self.first_trigger = first_trigger
        self.second_trigger = second_trigger

    def evaluate(self, story: NewsStory):
        return self.first_trigger.evaluate(story) or self.second_trigger.evaluate(story)


# ======================
# Filtering
# ======================
def filter_stories(stories, triggerlist):
    """
    Takes in a list of NewsStory instances.

    Returns: a list of only the stories for which a trigger in triggerlist fires.
    """
    triggered_stories = []
    for story in stories:
        is_fired = False
        for trigger in triggerlist:
            if trigger.evaluate(story):
                is_fired = True
        if is_fired:
            triggered_stories.append(story)
    return triggered_stories


# ======================
# User-Specified Triggers
# ======================
def read_trigger_config(filename):
    """
    filename: the name of a trigger configuration file

    Returns: a list of trigger objects specified by the trigger configuration
        file.
    """
    # Eliminate blank lines and comments.
    trigger_file = open(filename, "r")
    lines = []
    for line in trigger_file:
        line = line.rstrip()
        if not (len(line) == 0 or line.startswith("//")):
            lines.append(line)

    all_triggers = {}
    added_triggers = []

    for line in lines:
        arguments = line.split(',')
        # Trigger definitions.
        if arguments[0] != 'ADD':
            if arguments[1] == 'DESCRIPTION':
                trigger_name = arguments[0]
                trigger_phrase = arguments[2]
                all_triggers[trigger_name] = DescriptionTrigger(trigger_phrase)
            if arguments[1] == 'TITLE':
                trigger_name = arguments[0]
                trigger_phrase = arguments[2]
                all_triggers[trigger_name] = TitleTrigger(trigger_phrase)
            if arguments[1] == 'BEFORE':
                trigger_name = arguments[0]
                trigger_time = arguments[2]
                all_triggers[trigger_name] = BeforeTrigger(trigger_time)
            if arguments[1] == 'AFTER':
                trigger_name = arguments[0]
                trigger_time = arguments[2]
                all_triggers[trigger_name] = AfterTrigger(trigger_time)
            if arguments[1] == 'NOT':
                trigger_name = arguments[0]
                trigger_phrase = arguments[2]
                all_triggers[trigger_name] = NotTrigger(trigger_phrase)
            if arguments[1] == 'AND':
                trigger_name = arguments[0]
                first_composed_trigger = all_triggers[arguments[2]]
                second_composed_trigger = all_triggers[arguments[3]]
                all_triggers[trigger_name] = AndTrigger(first_composed_trigger, second_composed_trigger)
            if arguments[1] == 'OR':
                trigger_name = arguments[0]
                first_composed_trigger = all_triggers[arguments[2]]
                second_composed_trigger = all_triggers[arguments[3]]
                all_triggers[trigger_name] = OrTrigger(first_composed_trigger, second_composed_trigger)
        # Trigger addition.
        else:
            for i in range(1, len(arguments)):
                added_triggers.append(all_triggers[arguments[i]])

    return added_triggers


SLEEPTIME = 10  # seconds -- how often we poll


def main_thread(master):
    try:
        # t1 = TitleTrigger("election")
        # t2 = DescriptionTrigger("Trump")
        # t3 = DescriptionTrigger("Clinton")
        # t4 = AndTrigger(t2, t3)
        # t5 = TitleTrigger("India")
        # trigger_list = [t1, t4]

        # Reading the trigger configuration file
        trigger_list = read_trigger_config('triggers.txt')

        # Draws the popup window that displays the filtered stories
        # Retrieves and filters the stories from the RSS feeds
        frame = Frame(master)
        frame.pack(side=BOTTOM)
        scrollbar = Scrollbar(master)
        scrollbar.pack(side=RIGHT, fill=Y)

        t = "Google & Yahoo Top News"
        title = StringVar()
        title.set(t)
        ttl = Label(master, textvariable=title, font=("Helvetica", 18))
        ttl.pack(side=TOP)
        cont = Text(master, font=("Helvetica", 14), yscrollcommand=scrollbar.set)
        cont.pack(side=BOTTOM)
        cont.tag_config("title", justify="center")
        button = Button(frame, text="Exit", command=root.destroy)
        button.pack(side=BOTTOM)
        guidShown = []

        def get_cont(newstory):
            if newstory.get_guid() not in guidShown:
                cont.insert(END, newstory.get_title() + "\n", "title")
                cont.insert(END, "\n---------------------------------------------------------------\n", "title")
                cont.insert(END, newstory.get_description())
                cont.insert(END, "\n*********************************************************************\n", "title")
                guidShown.append(newstory.get_guid())

        while True:
            print("Polling . . .", end=" ")
            # Get stories from Google's Top Stories RSS news feed
            stories = process("http://news.google.com/news?output=rss")

            # The Yahoo's RSS feed no longer includes descriptions, so this flow is turned off.
            # stories.extend(process("http://news.yahoo.com/rss/topstories"))

            # Filter stories according to specified triggers.
            stories = filter_stories(stories, trigger_list)

            list(map(get_cont, stories))
            scrollbar.config(command=cont.yview)

            print("Sleeping...")
            time.sleep(SLEEPTIME)

    except Exception as e:
        print(e)


if __name__ == "__main__":
    root = Tk()
    root.title("Some RSS parser")
    t = threading.Thread(target=main_thread, args=(root,))
    t.start()
    root.mainloop()