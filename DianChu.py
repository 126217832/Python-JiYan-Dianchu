#coding=utf-8
"""
目标：获取国家企业信用信息公示系统http://www.gsxt.gov.cn/corp-query-homepage.html上的企业信息
技术点：采用极验点触型验证码
方案：利用超级鹰第三方平台识别
步骤：1，获取验证图片
     2，把图片发送给超级鹰后台
     3，超级鹰后台返回点触位置，模拟鼠标点击
工具：python2+selenium+chrome
"""

from time import sleep
import time
from io import BytesIO
from PIL import Image
import random
import tesserocr
from selenium import webdriver #浏览器驱动
from selenium.webdriver.chrome.options import Options #浏览器配置
from selenium.webdriver.support.ui import WebDriverWait #隐式等待元素加载
from selenium.webdriver.common.by import By #找到元素
from selenium.webdriver.support import expected_conditions as EC #等待元素出现的条件
from selenium.webdriver.common.action_chains import ActionChains #模拟鼠标的动作

from chaojiying import Chaojiying_Client

class DianChu():
    def __init__(self,**kwargs):
        self.start_time = time.time()
        self.search = kwargs.get('search') #查找的企业
        self.username = kwargs.get('username') #超级鹰用户名
        self.password = kwargs.get('password') #超级鹰密码
        self.id = kwargs.get('id') #超级鹰软件id
        self.captchatype = kwargs.get('captchatype') #超级鹰验证码类型
        self.chaojiying = Chaojiying_Client(self.username,self.password,self.id)
        self.url = kwargs.get('url') #请求url
        chrome_options = Options()
        chrome_options.add_argument('--user-data-dir=/home/ubuntu/.config/google-chrome/') #加载本地浏览器配置文件
        self.driver = webdriver.Chrome(chrome_options=chrome_options) #把配置加载进驱动
        self.driver.maximize_window() #屏幕最大
        self.wait = WebDriverWait(self.driver,3) #等待3秒

    def get_captcha(self):
        """获取验证码"""
        self.driver.get(self.url)
        search = self.wait.until(EC.presence_of_element_located((By.ID,'keyword'))) #输入框
        search.send_keys(self.search) #向输入框写入字段
        sleep(1)
        button = self.wait.until(EC.presence_of_element_located((By.ID,'btn_query'))) #点击按钮
        button.click() #点击搜索
        sleep(1)  # 等待验证框出现
        print('验证码加载耗时:%s'%(time.time()-self.start_time))
        try: #有验证框
            self.wait.until(
                EC.presence_of_element_located((By.XPATH, "//div[@style='display: block; opacity: 1;']")))

            start_time = time.time()
            image, filename = self.get_geetest_image_mitmdump()  # 获取验证码
            print('获取要发送到超级鹰验证码耗时:%s'%(time.time()-start_time))

            if type(image) != str: #如果从文件中获取坐标，则返回的是str类型
                try: #在发送验证前要判断是否不需要验证

                    start_time = time.time()
                    captcha = self.get_geetest_image_page(filename)
                    print('获取未点击验证码耗时:%s' % (time.time() - start_time))
                    if captcha.size[0] >300 and captcha.size[1] >300: #判断截取的图片大小再次判断是否不需要验证
                        print('第一阶段耗时:%s'%(time.time()-self.start_time))
                        start_time = time.time()
                        result = self.crack(image,self.captchatype)  # 发送到超级鹰后台验证
                        print('超级鹰耗时:%s'%(time.time()-start_time))
                        # print(result)
                        points = self.get_points(result)
                    else:
                        raise IOError
                except:
                    raise IOError
            else:
                points = [[int(number) for number in group.split(',')] for group in image.split('|')]
            start_time = time.time()
            self.use_click(points)  # 点击
            print('点击耗时:%s'%(time.time()-start_time))
            start_time = time.time()
            self.get_geetest_image_page(filename)  # 获取点击后的验证码,用来检验
            print('获取检验验证码耗时:%s'%(time.time()-start_time))
            self.affirm()  # 确认
            print('第二阶段耗时:%s'%(time.time()-self.start_time))
            start_time = time.time()
            sleep(1)
            try:
                self.wait.until(
                    EC.presence_of_element_located((By.XPATH, "//div[@style='display: block; opacity: 1;']")))
                pic_id = result.get('pic_id')
                position = result.get('pic_str')
                with open('./captcha/error.txt', 'ab+') as f:  # 把错误的信息保存
                    f.write('filename:%s,pic_id:%s,position:%s\n' % (filename, pic_id, position))
                start_time = time.time()
                face_num = self.get_face(filename)  # 获取验证汉字个数
                print('识别验证码字体个数耗时:%s'%(time.time()-start_time))
                print('face_num:%s'%face_num,'points_num:%s'%len(points))
                if len(points) != face_num and face_num!=0: #如果超级鹰返回的位置个数不等于需要验证的汉字个数，且汉字数不为0,则报错
                    print(self.chaojiying.ReportError(pic_id)) #报错

            except:
                position = result.get('pic_str')
                with open('./captcha/OK.txt', 'ab+') as f:  # 把正确的信息保存
                    f.write('filename:%s,position:%s\n' % (filename,position))
                print('登录成功')
                print('第三阶段耗时:%s' % (time.time() - start_time))

        except: #没有验证框
            print('登录成功')
        self.driver.quit()
        print('总耗时:%s'%(time.time() - self.start_time))

    def get_face(self,filename):
        """获取验证的字体的个数"""
        image = Image.open('./captcha/' + filename.split('.')[0] + '/' + 'original_' + filename)
        image = image.crop((0, 345, 116, 384)) #从验证图片中切割出字体
        image = image.resize((100,35))  # 调整图片大小，以便识别
        text1 = tesserocr.image_to_text(image, lang='chi_sim')  # 进行ocr识别，输出图片里的汉字
        image = image.resize((116,39))  # 调整图片大小，以便识别
        text2 = tesserocr.image_to_text(image, lang='chi_sim')  # 进行ocr识别，输出图片里的汉字
        image = image.resize((130,60))  # 调整图片大小，以便识别
        text3 = tesserocr.image_to_text(image, lang='chi_sim')  # 进行ocr识别，输出图片里的汉字
        max_num = max(len(text1),len(text2),len(text3)) #获取三个数的最大值
        return max_num/2 #汉字个数，需要除以2

    def affirm(self):
        """确认按钮"""
        affirm = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME,'geetest_commit_tip')))
        affirm.click()
    def use_click(self,points):
        """根据传入的点击位置进行点击"""
        self.affirming(points,random.uniform(0.5, 1))

    def affirming(self,points,randomtime):
        """执行点击验证码"""
        img = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'geetest_item_img')))
        for location in points: #在点击验证码之前先模拟鼠标滑过验证码，提高通过率
            ActionChains(self.driver).move_to_element_with_offset(img, location[0],location[1]).perform()

        for location in points:
            ActionChains(self.driver).move_to_element_with_offset(img, location[0],
                                                                  location[1]).click().perform()
            sleep(randomtime)  # 随机时间再次点击
    def get_points(self,result):
        """解析返回的结果，返回列表形式"""
        groups = result.get('pic_str').split('|')
        locations = [[int(number) for number in group.split(',')] for group in groups]
        return locations

    def crack(self,image,captchatype):
        """发送到超级鹰后台验证"""
        bytes_array = BytesIO()
        image.save(bytes_array, format='PNG')
        result = self.chaojiying.PostPic(bytes_array.getvalue(),captchatype)
        return result


    def get_position(self):
        """
        获取验证码位置
        :return: 验证码位置元组
        """
        img = self.wait.until(EC.presence_of_element_located((By.CLASS_NAME, 'geetest_item'))) #验证码位置
        location = img.location
        size = img.size
        top, bottom, left, right = location['y'], location['y'] + size['height'], location['x'], location['x'] + size[
            'width']
        return (top, bottom, left, right)

    def get_screenshot(self):
        """
        获取网页截图
        :return: 截图对象
        """
        screenshot = self.driver.get_screenshot_as_png()
        screenshot = Image.open(BytesIO(screenshot))
        return screenshot

    def get_geetest_image_page(self, name):

        top, bottom, left, right = self.get_position()
        # print(u'验证码位置', top, bottom, left, right)
        screenshot = self.get_screenshot()
        captcha = screenshot.crop((left, top, right, bottom))
        captcha.save('./captcha/'+name.split('.')[0]+'/crack_'+name.split('.')[0]+'.png')
        return captcha

    def get_geetest_image_mitmdump(self):
        """
        获取验证码图片
        :return: 图片对象
        """
        sleep(1) #等待代理脚本生成文件
        with open('./captcha/request.txt', 'r') as f:
            file = f.read() #加载代理脚本生成的图片路径 xxxx.jpg
        # 加载已经验证ok的图片路径，如果当前请求的验证码已经验证过了，就不用发出新的请求到超级鹰，直接用已经验证好的
        with open('./captcha/OK.txt', 'ab+') as f:
            OKFile = f.readlines()
        for info in OKFile:
            if file in info:
                position = info.split(':')[-1]
                return position,file
        image = Image.open('./captcha/'+file.split('.')[0]+'/'+file)
        return image,file

if __name__=='__main__':

    kwargs = {
        'url':'http://www.gsxt.gov.cn/corp-query-homepage.html',
        'search':u'阿里巴巴',
        'username':u'zlpdr520',
        'password':u'1262177832',
        'id':u'898459',
        'captchatype':9201
    }

    dianchu = DianChu(**kwargs)
    dianchu.get_captcha()
