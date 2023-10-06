from datetime import datetime
import re
from bs4 import BeautifulSoup
import asyncio
import csv
# from google.auth.transport import requests
import selenium
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.chrome.service import Service
# from webdriver_manager.chrom import ChromeDriverManager
import chromedriver_autoinstaller
import time
from konlpy import jvm
jvm.init_jvm(jvmpath="C:/Program Files/Java/jdk-20/bin/server/jvm.dll")  # 경로는 실제 JDK 경로에 맞게 변경
import pandas as pd
from konlpy.tag import Okt
import matplotlib.pyplot as plt
from wordcloud import WordCloud
import collections
from selenium.webdriver.common.by import By
import os


url ="https://store.steampowered.com/"
print("게임 이름을 입력하세요.")
game = input()
game_id = 0


async def crawl(url):
    options = webdriver.ChromeOptions()

    #크롬 드라이버 로드
    # driver = webdriver.Chrome(options = options, executable_path="chromedriver")
    chromedriver_autoinstaller.install()
    driver = webdriver.Chrome()
    # driver = webdriver.Chrome(chrome_driver="chromedriver")
    await asyncio.get_event_loop().run_in_executor(None, driver.get, url)
    time.sleep(1)

    #게임 검색
    element = driver.find_element(By.XPATH, '//*[@id="store_nav_search_term"]')
    element.send_keys(game)
    element.send_keys("\n")
    time.sleep(2)

    ## 게임 탐색 & 예외처리 ###########################################################
    try:
        element = driver.find_element(By.XPATH, '//*[@id="search_resultsRows"]/a[1]')
        if(element != None):
            element.click()
            time.sleep(1)
            # 현재 url 가져오기
            nurl = driver.current_url
            # 게임 id 가져오는 것
            pattern = r"https://store.steampowered.com/app/(\d+)/"
            # 이건 성인인증 해야하는 것
            match = re.search(pattern, nurl)
            if(match == None):
                pattern = r"https://store.steampowered.com/agecheck/app/(\d+)/"
                match = re.search(pattern, nurl)
            if match:
                number = match.group(1)  # 게임 고유 ID
            print(nurl)
            # 리뷰 url로 이동
            driver.get("https://steamcommunity.com/app/" + number + "/reviews/?browsefilter=toprated&snr=1_5_100010_&filterLanguage=koreana")
            game_id = number
        time.sleep(2)

        ## 데이터 크롤링 #####################################################

        # 한글 클릭을 통해 언어 설정 변경
        element = driver.find_element(By.XPATH, '// *[ @ id = "language_pulldown"]')
        element.click()
        element2 = driver.find_element(By.XPATH, '//*[@id="language_dropdown"]/div/a[4]')
        element2.click()
        time.sleep(2)

        # 스크롤 내리기 이동 전 위치
        scroll_location = driver.execute_script("return document.body.scrollHeight")
        while True:
            # 현재 스크롤의 가장 아래로 내림
            driver.execute_script("window.scrollTo(0,document.body.scrollHeight)")
            # 전체 스크롤이 늘어날 때까지 대기
            time.sleep(1.5)
            # 늘어난 스크롤 높이
            scroll_height = driver.execute_script("return document.body.scrollHeight")
            # 늘어난 스크롤 위치와 이동 전 위치 같으면(더 이상 스크롤이 늘어나지 않으면) 종료
            if scroll_location == scroll_height:
                break
            # 같지 않으면 스크롤 위치 값을 수정하여 같아질 때까지 반복
            else:
                # 스크롤 위치값을 수정
                scroll_location = driver.execute_script("return document.body.scrollHeight")

        html = driver.page_source

        like_list = []  # 좋아요가 들어갈 리스트
        date_list = []  # date가 들어갈 리스트
        comment_list = []  # review가 들어갈 리스트
        good_list = []  # good가 들어갈 리스트
        soup = BeautifulSoup(html, "html.parser")

        # 좋아요 여부 가져옴
        likes = soup.find_all("div", attrs={"class": "title"})
        for like in likes:
            a = "추천"
            b = "비추천"
            if b in like.text.strip():
                like_list.append(int(0))
            elif a in like.text.strip():
                like_list.append(int(1))

        # date 가져옴
        dates = soup.find_all("div", attrs={"class": "date_posted"})
        for date in dates:
            date = datetime.strptime(date.text.strip(), "게시 일시: %Y년 %m월 %d일").date()
            date_list.append(date)

        # comment 가져옴
        comments = soup.find_all("div", attrs={"class": "apphub_CardTextContent"})
        for comment in comments:
            comment.find(class_="date_posted").decompose()

            # dynamiclink_box 제거
            dynamic_link = comment.find(class_= "dynamiclink_box")
            if dynamic_link:
                dynamic_link.decompose()

            # early_access_review 제거 및 문자열 변환
            if (comment.find(class_="early_access_review") != None):
                comment.find(class_="early_access_review").decompose()
                # comment = re.findall(r'[가-힣a-zA-Z]+', str(comment))
                # if comment:
                #     comment = ''.join(comment)
            comment_text = comment.text.strip()
            comment_list.append(str(comment_text))

        # good 가져옴
        goods = soup.find_all("div", attrs={"class": "found_helpful"})
        for good in goods:
            good.find(class_="review_award_aggregated tooltip").decompose()
            good = str(good.text.strip())
            good = re.findall(r'\d+', good)
            good = [int(num) for num in good]
            good = sum(good)
            good_list.append(good)


        # game_id로 된 파일을 생성
        if not os.path.exists(game_id):
            os.makedirs(game_id)


        # 크롤링한 내용을 CSV 파일에 저장
        with open(game_id+"/"+game_id+".csv", mode="w", newline="", encoding="utf-8") as file:
            writer = csv.writer(file)
            writer.writerow(["Game", "like", "date", "comment", "good"])
            # 리스트 길이중 가장 긴 길이 구함
            max_length = max(len(like_list), len(date_list), len(comment_list))

            for i in range(max_length):
                like = like_list[i]
                date = date_list[i]
                comment = comment_list[i]
                good = good_list[i]
                writer.writerow([game, like, date, comment, good])

        driver.quit()

        ## csv파일 ansi로 변경###################################################

        # csv 파일 불러오기
        file_path = game_id+"/"+game_id+'.csv'  # 파일 경로
        df = pd.read_csv(file_path, encoding='utf-8')
        # 특정 열 선택
        target_column = 'comment'  # 대상 열 이름
        data = df[target_column]
        # 숫자와 특수문자 제거하여 한글과 영어만 남기기
        filtered_data = data.str.replace('[^가-힣a-zA-Z]+', ' ', regex=True)
        filtered_data = filtered_data.astype(str)
        df[target_column] = filtered_data  # 기존 열 대체
        # 처리된 데이터를 csv 파일로 저장
        output_file_path = game_id+"/"+game_id+'.csv'  # 저장할 파일 경로
        df.to_csv(output_file_path, index=False, encoding="ansi")

        ##워드 클라우드 #######################################################
        file_name = game_id+".csv"
        dfL = pd.read_csv(file_path, encoding='cp949')
        dfN = pd.read_csv(file_path, encoding='cp949')

        dfL['comment'] = dfL['comment'].astype(str)
        dfN['comment'] = dfN['comment'].astype(str)

        # 불용어 제거
        dfL['comment'] = dfL['comment'].str.replace("[^ᄀ-하-ᅵ가-힣]", "")
        dfN['comment'] = dfN['comment'].str.replace("[^ᄀ-하-ᅵ가-힣]", "")

        dfL = dfL[dfL['like'] == 1]
        dfN = dfN[dfN['like'] == 0]

        # print(dfL['comment'])
        # print("============")
        # print(dfN['comment'])

        # 형태소 토큰화
        stopword = ['게임', '업데이트', '끼리', '같음', '나중', '그',
                    '좀', '이', '것', '수', '겜', '입니다', '때',
                    '정도', '같은', '이런', '모습', '그냥', '별로',
                    '있는', '쪽', '어떻게', '제품', '가지', '끼리',
                    '본', '임', '나중', '제발', '거의', '업뎃', '없',
                    '썅년', '함', '그렇고', '닥', '좀더', '같은것도',
                    '얘', '뭐', '게', '없고', '명', '박스', '땅', '음애',
                    '있는지', '거', '애초', '라면', '거기', '언공', '점',
                    '를', '함', '진짜', '더', '진짜', '조금', '거', '보고',
                    '안', '있음', '하나', '왜', '더', '안']
        okt = Okt()
        temp_list = []
        for sentence in dfL['comment']:
            # print(dfL['comment'])
            s_list = okt.pos(sentence)
            for word, tag in s_list:
                if word not in stopword:
                    if tag in ['Noun', 'Adjective']:
                        temp_list.append(word)
        counts = collections.Counter(temp_list)
        tagL = counts.most_common(10)
        # print(tagL)

        okt = Okt()
        temp_list = []
        for sentence in dfN['comment']:
            # print(dfN['comment'])
            s_list = okt.pos(sentence)
            for word, tag in s_list:
                if word not in stopword:
                    if tag in ['Noun', 'Adjective']:
                        temp_list.append(word)
        counts = collections.Counter(temp_list)
        tagN = counts.most_common(10)
        # print(tagN)

        font_path = 'C:/Windows/Fonts/malgun.ttf'
        wc = WordCloud(font_path=font_path, background_color='white', max_font_size=60)
        cloud = wc.generate_from_frequencies(dict(tagL))
        plt.imshow(cloud)
        plt.savefig(game_id+"/"+game_id + 'L.png', dpi=300)
        plt.show()


        cloud = wc.generate_from_frequencies(dict(tagN))
        plt.imshow(cloud)
        plt.savefig(game_id+"/"+game_id + 'N.png', dpi=300)
        plt.show()




    except NoSuchElementException:
        print(game+" 요소를 찾을 수 없습니다.")




async def main():
    await crawl(url)

loop = asyncio.get_event_loop()
loop.run_until_complete(main())