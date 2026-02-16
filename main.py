from Config import Config
from ApiService import ApiService

Config.load()
token = ApiService.get_azure_access_token()
print(token)
# def fetch_devices():
#     get_azure_access_token()
#
#     platforms = {
#         "intune": "https://graph.microsoft.com/v1.0/deviceManagement/managedDevices",
#         "azure": "https://graph.microsoft.com/v1.0/devices"
#     }
#
#     azure_devices = []
#     intune_devices = []
#     azure_user_map = {}
#     azure_queue = Queue()
#
#     with ThreadPoolExecutor(max_workers=3) as executor:
#         futures = {
#             executor.submit(
#                 fetch_all_devices_from_platform,
#                 platform,
#                 url,
#                 azure_queue if platform == "azure" else None,
#                 azure_devices if platform == "azure" else None,
#                 intune_devices if platform == "intune" else None
#             ): platform
#             for platform, url in platforms.items()
#         }
#
#         # Start user lookup thread
#         user_thread = Thread(target=user_batch_worker, args=(azure_queue, azure_user_map))
#         user_thread.start()
#
#         # Wait for both fetch threads
#         for future in as_completed(futures):
#             platform = futures[future]
#             try:
#                 future.result()
#                 print(f"[✓] Finished fetching {platform} devices.")
#             except Exception as e:
#                 print(f"[✗] Error fetching {platform}: {e}")
#
#         user_thread.join()
#
#     print(f"\n[Summary]")
#     print(f"Azure Devices: {len(azure_devices)}")
#     print(f"Intune Devices: {len(intune_devices)}")
#     print(f"Azure Devices with User IDs: {len(azure_user_map)}")
#
#     # assigning users for azure devices
#     for azure_device in azure_devices:
#         azure_device.user_id = azure_user_map.get(azure_device.id)
#
#     devices = {}
#
#     # ORDER IS VERY IMPORTANT HERE< AZURE FIRST< INTUNE AFTER, INTUNE MUST OVERWRITE SOME OF AZURE
#     # Add Azure devices
#     for device in azure_devices:
#         if device.topdesk_asset_name:
#             devices[device.topdesk_asset_name] = device
#
#     # Add Intune devices (overwrites if name matches)
#     for device in intune_devices:
#         if device.topdesk_asset_name:
#             devices[device.topdesk_asset_name] = device
#
#     return devices
#
#
# # Fetch devices and assets
# all_devices, all_assets = fetch_devices_and_assets_in_parallel()