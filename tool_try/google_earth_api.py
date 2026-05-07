import ee
import requests
import os
import time
from tqdm import tqdm

# --- 1. 初始化 ---
# 1. 触发认证流程
try:
    ee.Authenticate(auth_mode="notebook")
    print("认证链接已生成，请在浏览器中打开并完成授权。")
    ee.Initialize(project="ee-charles1xjy")
    print("GEE 初始化成功！")
except Exception as e:
    print(f"认证出错: {e}")

# 2. 初始化 API
# 注意：如果你使用的是 Google Cloud Project，请填入你的项目 ID
# ee.Initialize(project='your-project-id')


# --- 2. 设置路径 ---
base_dir = os.getcwd()
target_folder = os.path.join(base_dir, "../Google_earth")

if not os.path.exists(target_folder):
    os.makedirs(target_folder)
    print(f"✅ 已创建文件夹: {target_folder}")


# --- 3. 定义带进度的下载函数 ---
def download_oracle_arena(lon, lat, year):
    # 1. 修改坐标：美国加州奥克兰 甲骨文球馆
    # 注意：西经是负数！
    # lon, lat = -122.2030, 37.7503

    # 替换为大通中心的坐标

    # buffer(400) 意味着提取 800x800米 的区域，刚好框住球馆和停车场
    roi = ee.Geometry.Point([lon, lat]).buffer(400).bounds()

    # NAIP 数据不是每年都有（通常一个州每2-3年拍一次）
    # 所以我们把时间范围放宽到该年份往前推2年，确保能拿到图
    start_date = f"{year - 2}-01-01"
    end_date = f"{year}-12-31"

    try:
        # 2. 修改卫星：换成超高清的 NAIP 数据集
        collection = (
            ee.ImageCollection("USDA/NAIP/DOQQ")
            .filterBounds(roi)
            .filterDate(start_date, end_date)
            .sort("system:time_start", False)
        )  # 优先取最新的

        count = collection.size().getInfo()
        if count == 0:
            return f"跳过: {year} 年附近没有找到 NAIP 影像。"

        # 现在改成这样：把所有相关的图拼起来
        dataset = collection.mosaic()

        # 3. 修改波段：NAIP 原生就是 8位 RGB 图片 (0-255)
        # 波段名字也变成了 R(红), G(绿), B(蓝)
        vis_params = {"bands": ["R", "G", "B"], "min": 0, "max": 255}

        url = dataset.visualize(**vis_params).getThumbURL(
            {"region": roi, "dimensions": 1024, "format": "jpg"}
        )

        file_name = f"Oracle_Arena_{year}.jpg"
        save_path = os.path.join(target_folder, file_name)

        r = requests.get(url, timeout=60)
        if r.status_code == 200:
            with open(save_path, "wb") as f:
                f.write(r.content)
            return f"成功: {file_name}"
        else:
            return f"失败: {year} 年请求返回状态码 {r.status_code}"

    except Exception as e:
        return f"异常: {year} 年处理出错 -> {str(e)}"


# --- 4. 执行主循环 ---
years_to_download = [2016, 2019, 2024]

print(f"\n🚀 开始下载任务，共 {len(years_to_download)} 个年份...")
target_lon, target_lat = -122.3879, 37.7680
with tqdm(total=len(years_to_download), desc="总进度", unit="img") as pbar:
    for year in years_to_download:
        pbar.set_postfix_str(f"正在处理 {year}")
        # 调用新函数
        result = download_oracle_arena(target_lon, target_lat, year)
        tqdm.write(result)
        pbar.update(1)

print(f"\n✨ 任务全部结束！")
