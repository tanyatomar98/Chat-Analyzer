import os
from typing import Counter
import streamlit as st
import pandas as pd
import plotly.express as px
import re
import emoji
from wordcloud import WordCloud, STOPWORDS, ImageColorGenerator
import altair as alt

# ([0-2][0-9]|(3)[0-1]) -> date
# (\/) -> / or \
# (((0)[0-9])|((1)[0-2])) -> month
# (\d{2}|\d{4}) -> \d for digit {2} for 2 digits and {4} for four digits
# \s* -> 0 or more space
# ([0-9][0-9]):([0-9][0-9]) -> Hour:Minutes format

st.title("WhatsApp Chat Analysis")

def isDateTime(s):
    patterns = '^\d{1,2}/\d{1,2}/\d{1,2}, \d{1,2}:\d{1,2}\S -'

    date_exist = re.match(patterns, s)
    if date_exist:
        return True
    else:
        return False

# Check for author in message


def isAuthor(s):
    # First check for semicolon in string
    s = s.split(':')
    if len(s) == 1:
        return False
    else:
        return True


# parsed message data from given data
def getData(s):
    split_line = s.split('-')  # split date_time[0] && author_msg[1]
    date, time, author, msg = None, None, None, None

    date_time = split_line[0]
    date = split_line[0].split(',')[0].strip()
    time = split_line[0].split(',')[1].strip()

    msg = "".join(split_line[1:])

    if isAuthor(msg):
        split_dt = msg.split(':')
        author = split_dt[0].strip()
        msg = "".join(split_dt[1:])
        msg = msg.strip()
    return date, time, author, msg

uploadFile = st.file_uploader("Choose WhatsApp Chat to upload(.txt file only)", type="txt")
date, time, author = None, None, None
msgBuffer = []  # to store multiline msg
verify_data = []
if uploadFile is not None:
    for line in uploadFile:
        line = line.decode("utf-8")
        # st.write(line)
        line = line.strip()
        if isDateTime(line):
                if len(msgBuffer) > 0:
                    verify_data.append([date, time, author, " ".join(msgBuffer)])
                msgBuffer.clear()
                date, time, author, msg = getData(line)
                # st.write(date,time,author,msg)
                msgBuffer.append(msg)
                # st.write(msgBuffer)
        else:
            msgBuffer.append(line)

if verify_data:
    #############################################################################
    # create dataframe
    df = pd.DataFrame(verify_data, columns=['Date', 'Time', 'Author', 'Message'])
    # convert the Date column to contain date format
    df['Date'] = pd.to_datetime(df['Date']).dt.date

    # total message
    totalMsg = df['Message'].value_counts().sum()

    # message per auth
    totalMsgPerAuthor = df['Author'].value_counts().head(5)

    # media message
    mediaMsg = df[df['Message'] == "<Media omitted>"]
    totalMediaMsg = mediaMsg['Author'].value_counts()

    # none author 
    noAuthor = df[df['Author'].isnull()]
    # deleted message
    deleteMsg = df[df['Message'] == 'This message was deleted']
    totalDeleteMsg = deleteMsg.value_counts()

    #############################################################################
    # total message & media message
    col1, col2 = st.columns(2)
    with col1:   
        # total message
        st.markdown(">Total Message")
        st.header(f"{totalMsg}")     
    with col2:
        # delete message
        st.markdown(">Delete Message")
        st.header(totalDeleteMsg.sum())


    # message per author
    st.subheader(f"Message per Author")
    cols = st.columns(len(totalMsgPerAuthor))
    for index, (key,value) in enumerate(totalMsgPerAuthor.items()):
        with cols[index]:
            st.markdown(key)
            st.subheader(value)

    st.bar_chart(totalMsgPerAuthor)



    # media message
    st.subheader("Total Media Message")
    st.header(f"{totalMediaMsg.sum()}")
        
    # plot media msg per author bar chart
    st.line_chart(totalMediaMsg)

    ##################################################################

    # remove media, deleted, unknown author message
    message_df = df.drop(mediaMsg.index)
    message_df = message_df.drop(noAuthor.index)
    message_df = message_df.drop(deleteMsg.index)
    # convert all msg to lower case
    message_df["Message"] = message_df["Message"].apply(lambda s: s.lower() )
    # create columns Words which contain list of words in column
    message_df['Words'] = message_df["Message"].apply(lambda s: s.split(' '))
    # create column TotalWords which contain total words in column
    message_df['TotalWords'] = message_df["Message"].apply(lambda s: len(s.split(' ')))
    # is message or emoji message
    message_df['EmojiCount'] = message_df['Message'].apply(lambda s: emoji.is_emoji(s))
    # overall words frquency
    wordsCount = message_df['TotalWords'].value_counts().head(10)
    # total words per author
    totalWordsCountPerAuthor = message_df[["TotalWords", "Author"]].groupby("Author").sum()
    ##################################################################
    st.subheader("Words Analysis")


    col1, col2 = st.columns(2)
    with col1:
        st.bar_chart(wordsCount)
    with col2:
        st.bar_chart(totalWordsCountPerAuthor)


    ##################################################################

    # date the message send most
    totalMsgByDate = message_df['Date'].value_counts().head(5)
    # show bar chart for max message send on which date
    st.subheader("Message Counts by Date")
    st.line_chart(totalMsgByDate)


    # time the message can get reply
    st.subheader("Message Counts by time")
    totalMsgByTime = message_df['Time'].apply(lambda h: h.split(':')[0]).value_counts().head(10)
    st.line_chart(totalMsgByTime)


    def isEmoji(text):
        emojiList = []
        extractEmoji = emoji.emoji_list(text) #extract all emojis from the string 
        # return -> [{'match_start': 10, 'match_end': 11, 'emoji': '👍'}, {'match_start': 7, 'match_end': 11, 'emoji': '😛'}]
        for dictionary in extractEmoji: # loop from list
            getEmoji = dictionary['emoji'] # extract value of emoji from dictionary
            emojiList.append(getEmoji) # append to our emoji list
        return emojiList

    # create emoji column to message_df
    message_df['Emoji'] = message_df['Message'].apply(isEmoji)
    # set of unique emoji in complete chat
    setOfEmoji = list(set([e for emojiList in message_df['Emoji'] for e in emojiList]))

    # list of emoji (can have same emoji)
    listOfEmoji = list([e for emojilist in message_df['Emoji'] for e in emojilist] )
    dictOfEmoji = dict(Counter(listOfEmoji)).items()
    # sorting the dictionary on behalf of no. of emojis tuple[1]
    dictOfEmoji = sorted(dictOfEmoji, key=lambda x: x[1], reverse=True) # x -> each dataset inside the dict {(a,1)(dataset)}

    emoji_df = pd.DataFrame(dictOfEmoji, columns=['Emoji', 'Count'])
    pieChart = px.pie(emoji_df, values="Count", names="Emoji")
    pieChart.update_traces(textposition='inside', textinfo = "percent+label")
    st.subheader("Top Emoji")
    st.plotly_chart(pieChart, use_container_width=True)

    # contain all words of whole chat
    text = ' '.join(msg.lower() for msg in message_df['Message'])

    wordImage = WordCloud(stopwords=STOPWORDS,background_color='white').generate(text)
    st.subheader("Word Cloud")
    st.image(wordImage.to_array())


    # # top 10 words in a chat
    # words = message_df['Words']
    # # combine all the list in one
    # wordsList = list(i.lower() for word in words for i in word)
    # # counter-> count frequency of word and make dictionary {0: ('ha': 200), ...}
    # wordsDict = dict(Counter(wordsList)).items()
    # # sort the dict on the basis of counting -> return list with top 10 words
    # wordsDict = sorted(wordsDict, key=lambda x: x[1], reverse=True)[80:90]
    # st.subheader("Top 10 Words")
    # for index, (key,value) in enumerate(wordsDict):
    #     st.write(key,value)

    st.subheader("Top 10 Message")
    # remove emoji message
    emojiMsg = message_df[message_df['EmojiCount'] != False]
    message_df = message_df.drop(emojiMsg.index)
    # top 10 message in chat
    topMsg = message_df['Message'].value_counts().head(10)
    pxMsg = px.bar(topMsg)
    st.plotly_chart(pxMsg)
elif uploadFile & (verify_data==[]):
    st.header("File Containe unwanted data")
    
else:
    st.header("Upload File to see data")
