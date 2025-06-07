import ydb
import os
driver_config = ydb.DriverConfig(
    'grpcs://ydb.serverless.yandexcloud.net:2135', '/ru-central1/b1gktmqejq0mj6dof4bb/etnqh8n6c2k8cori6mqu',
    credentials=ydb.credentials_from_env_variables(os.getenv("AUTH")),

)
print(driver_config)
with ydb.Driver(driver_config) as driver:
    try:
        driver.wait(timeout=15)
    except TimeoutError:
        print("Connect failed to YDB")
        print("Last reported errors by discovery:")
        print(driver.discovery_debug_details())

