"""全局 conftest：只放所有测试共用的钩子"""
import os
from datetime import datetime
import pytest
from pytest_html import extras


@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    """测试失败时自动截图：落盘 + 嵌进 HTML 报告"""
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        driver = (
            item.funcargs.get("driver")
            or item.funcargs.get("logged_in_driver")
            or item.funcargs.get("clean_driver")
        )
        if driver:
            screenshots_dir = os.path.join(
                os.path.dirname(os.path.abspath(__file__)), "screenshots"
            )
            os.makedirs(screenshots_dir, exist_ok=True)
            filename = f"{item.name}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.png"
            filename = filename.replace("/", "_").replace("\\", "_").replace(":", "_")
            filepath = os.path.join(screenshots_dir, filename)
            driver.save_screenshot(filepath)
            print(f"\n[截图] 失败截图已保存：{filepath}")

            # 把截图嵌进 HTML 报告
            report.extras = getattr(report, "extras", [])
            report.extras.append(extras.image(filepath))