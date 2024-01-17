from flask import Flask
from flask import request
import json
import traceback
import asyncio
import aiohttp
import re
from typing import Union
from urllib.parse import unquote

app = Flask(__name__)


# api_url = '2.51 trr:/ U@Y.mD 09/04 “号称无极的世界两极分化严重，一个活生生的人只值十元” # 武侠 # 张柏芝 # 谢霆锋  https://v.douyin.com/iLD7btHw/ 复制此链接，打开Dou音搜索，直接观看视频！'

headers = { 'User-Agent': "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36"}

douyin_api_headers = {
    'accept-encoding': 'gzip, deflate, br',
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/109.0.0.0 Safari/537.36',
    'Referer': 'https://www.douyin.com/',
    'cookie': ''
}


def get_url(text: str) -> Union[str, None]:
    try:
        # 从输入文字中提取索引链接存入列表/Extract index links from input text and store in list
        url = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', text)
        # 判断是否有链接/Check if there is a link
        if len(url) > 0:
            return url[0]
    except Exception as e:
        print('Error in get_url:', e)
        return None
    
def relpath(file):
    """ Always locate to the correct relative path. """
    from sys import _getframe
    from pathlib import Path
    frame = _getframe(1)
    curr_file = Path(frame.f_code.co_filename)
    return str(curr_file.parent.joinpath(file).resolve())
## 转换短链接
async def convert_share_urls(url: str) -> Union[str, None]:
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(url, headers=headers, proxy=None, allow_redirects=False,
                                    timeout=10) as response:
                if response.status == 302:
                    url = response.headers['Location'].split('?')[0] if '?' in response.headers[
                        'Location'] else \
                        response.headers['Location']
                    print('获取原始链接成功, 原始链接为: {}'.format(url))
                    return url
    except Exception as e:
        print('获取原始链接失败！')
        print(e)
        raise e
    else:
        print('该链接为原始链接,无需转换,原始链接为: {}'.format(url))
    return url

def get_douyin_video_id(video_url: str) -> Union[str, None]:
     # 正则匹配出视频ID
        try:
            # 链接类型:
            # 视频页 https://www.douyin.com/video/7086770907674348841
            if '/video/' in video_url:
                key = re.findall('/video/(\d+)?', video_url)[0]
                # print('获取到的抖音视频ID为: {}'.format(key))
                return key
            # 发现页 https://www.douyin.com/discover?modal_id=7086770907674348841
            elif 'discover?' in video_url:
                key = re.findall('modal_id=(\d+)', video_url)[0]
                # print('获取到的抖音视频ID为: {}'.format(key))
                return key
            # 直播页
            elif 'live.douyin' in video_url:
                # https://live.douyin.com/1000000000000000000
                video_url = video_url.split('?')[0] if '?' in video_url else video_url
                key = video_url.replace('https://live.douyin.com/', '')
                # print('获取到的抖音直播ID为: {}'.format(key))
                return key
            # note
            elif 'note' in video_url:
                # https://www.douyin.com/note/7086770907674348841
                key = re.findall('/note/(\d+)?', video_url)[0]
                # print('获取到的抖音笔记ID为: {}'.format(key))
                return key
        except Exception as e:
            print('获取抖音视频ID出错了:{}'.format(e))
            return None
        
async def get_douyin_video_data(video_id: str) -> Union[dict, None]:
        """
        :param video_id: str - 抖音视频id
        :return:dict - 包含信息的字典
        """
        try:
            # 构造访问链接/Construct the access link
            api_url = "https://www.iesdouyin.com/web/api/v2/aweme/iteminfo/?item_ids=%s&a_bogus=64745b2b5bdc4e75b720a9a85b19867a" % video_id
            # api_url = self.generate_x_bogus_url(api_url)
            # 访问API/Access API
            print("正在请求抖音视频API: {}".format(api_url))
            async with aiohttp.ClientSession() as session:
                douyin_api_headers['Referer'] = f'https://www.douyin.com/video/{video_id}'
                async with session.get(api_url, headers=douyin_api_headers, proxy=None,
                                        timeout=10) as response:
                    response = await response.json()
                    video_data = response['item_list'][0]
                    # print('获取视频数据成功！')
                    # print("抖音API返回数据: {}".format(video_data))
                    return video_data
        except Exception as e:
            raise ValueError(f"获取抖音视频数据出错了")

@app.route('/dyvideos', methods=['POST'])
def do_task():
    try:
        form_data = dict(request.form)
        content = form_data.get('content')
        url = get_url(content)
        url = re.compile(r'(https://v.douyin.com/)\w+', re.I).match(url).group()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        task = loop.create_task(convert_share_urls(url))
        loop.run_until_complete(task)
        base_url = task.result()
        video_id = get_douyin_video_id(base_url)
        loop.close()
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        task = loop.create_task(get_douyin_video_data(video_id))
        loop.run_until_complete(task)
        red_data = task.result()
        loop.close()
        return json.dumps({"code": 0, "msg":"success", "data": red_data})
    except:
        err_msg = 'url: %s, err_msg: %s' % (request.url, (str(traceback.format_exc())))
        print(err_msg)
        return json.dumps({"code": -1, "msg":"failed", "data": 0})
    

if __name__ == '__main__':
    app.run("0.0.0.0", debug=False, port=6006)