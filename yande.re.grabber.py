# yande.re.grabber
#
# https://github.com/voidtemp/yande.re.grabber
#
# Images grabber for yande.re.
#
# Modify paths, number of parallel downloads, copy tags string from browser url, set first and last pages and run.
#
# Some useful tags:
# mpixels:>10 shown:true https://yande.re/post?tags=mpixels%3A%3E10+shown%3Atrue
# width:>2000 width:<3000 height:>6000 https://yande.re/post?tags=width%3A%3E2000+width%3A%3C3000+height%3A%3E6000
#
# More: https://yande.re/help/cheatsheet
#

import urllib3
import urllib.parse
import re
import pathlib
import sys
from multiprocessing import Lock
from pathvalidate import sanitize_filepath
from concurrent.futures import ThreadPoolExecutor

MIN_HIGHRES_SIZE = 6000 #px, minimum size of width or height for image to be considered high resolution
PARALLEL_DOWNLOADS = 6
OUT_PATH = r'E:\daki\'
OUT_PATH_LOWRES = r'E:\daki\lowres\'

#global
totalCount = 1
http = urllib3.PoolManager(maxsize=PARALLEL_DOWNLOADS, block=True)
totalCountMutex = Lock()
printMutex = Lock()

urllib3.disable_warnings()

def printMessage(message):
    global printMutex

    printMutex.acquire()
    print(message)
    sys.stdout.flush()
    printMutex.release()

def isLowRes(w, h):
    return w < MIN_HIGHRES_SIZE and h < MIN_HIGHRES_SIZE

def getImageSize(pageText):
    match = re.search('<li>Size: (?P<width>\d*)x(?P<height>\d*)<\/li>', pageText)

    if match:
        return int(match.group('width')), int(match.group('height'))

    return -1, -1


def processFile(pageUrl, pageText, w, h):
    global totalCount
    global totalCountMutex
    global http

    logMessage = pageUrl + ' finished: size= ' + str(w) + ' x ' + str(h)

    if isLowRes(w, h):
        logMessage += ' (lowres)'

    url = ""
    matchPng = re.search('href="(?P<Url>.*)">Download PNG.*<\/a>', pageText)

    if matchPng:
        logMessage += ', PNG'
        url = matchPng.group('Url')
    else:
        matchJPG1 = re.search('href="(?P<Url>.*)">Download \(.*JPG.*<\/a>', pageText)

        if matchJPG1:
            url = matchJPG1.group('Url')
        else:
            matchJPG2 = re.search('href="(?P<Url>.*)">Download larger version.*<\/a>', pageText)

            if matchJPG2:
                url = matchJPG2.group('Url')
            else:
                printMessage(logMessage + ' ========================= error link not found')
                return

        logMessage += ', JPG'

    url = url.replace("yande.re/sample/", "yande.re/image/")
    fileName = sanitize_filepath(urllib.parse.unquote(re.match('.*\/(?P<name>.*)', url).group('name')), "_")

    r = http.request('GET', url)

    if len(r.data) == 0:
        printMessage(logMessage + ' ========================= error failed to get file')
        return
    else:
        path = OUT_PATH_LOWRES if isLowRes(w, h) else OUT_PATH

        with open(path + fileName, 'wb') as fout:
            fout.write(r.data)

        totalCountMutex.acquire()
        count = totalCount
        totalCount += 1
        printMessage(logMessage + ', success (' + str(count) + ').')
        totalCountMutex.release()


def processPost(url):
    global http

    printMessage(url + ' started...')

    r = http.request('GET', "https://yande.re" + url)
    content = r.data.decode('utf-8');
    w, h = getImageSize(content)

    if w == -1 or h == - 1:
        printMessage(url + " ========================= error w == -1 or h == - 1")
        return

    processFile(url, content, w, h)


def processPosts(pageNumber, pageText, isLastPage):
    matches = re.findall('class="thumb" href="(\/post\/show\/\d*)"', pageText)
    postsNumber = len(matches)

    printMessage('page: ' + str(pageNumber) + ', posts: ' + str(postsNumber))

    if postsNumber != 40 and not isLastPage:
        print('Wrong posts number. Expected 40, got ' + str(postsNumber))
        return False;

    with ThreadPoolExecutor(max_workers=PARALLEL_DOWNLOADS) as executor:
        executor.map(processPost, matches)

    return True

def processYandere(firstPage, lastPage, tags):
    global http

    printMessage('Begin with tags "' + tags + '"')

    for pageNumber in range(firstPage, lastPage + 1):
        url = 'https://yande.re/post?page=' + str(pageNumber) + '&tags=' + tags
        r = http.request('GET', url)

        if len(r.data) == 0:
            printMessage(' ======== error get page ' + str(pageNumber))
            return

        if not processPosts(pageNumber, r.data.decode('utf-8'), pageNumber == lastPage):
            break

    printMessage('Done.')

###############
pathlib.Path(OUT_PATH).mkdir(parents=True, exist_ok=True)
pathlib.Path(OUT_PATH_LOWRES).mkdir(parents=True, exist_ok=True)

processYandere(1, 172, 'dakimakura')
#processPost('/post/show/419814')