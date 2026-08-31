# =============================================================================
# NovelFetch - Buildozer spec for the Android (KivyMD) app.
#
# The repo shares code: sources/ + core/ live at the repo root, while the
# KivyMD UI is gui/. Buildozer launches the repo-root main.py, which
# dispatches to gui.main on Android.
#
# To build:  (must be run on Linux x86_64 with Docker, or with an Android SDK)
#     pip install buildozer
#     buildozer android debug
# =============================================================================

[app]

# (str) Title of your application
title = NovelFetch

# (str) Package name
package.name = novelfetch

# (str) Package domain (needed for android/ios packaging)
package.domain = org.novelfetch

# (str) Source code where the main.py live. Repo root holds main.py (the
# dispatcher) AND the shared modules, so everything gets packaged together.
source.dir = .

# (list) Source files to include (let empty to include all the files)
source.include_exts = py,png,jpg,kv,atlas,gif,ttf

# (list) List of inclusions using pattern matching
#source.include_patterns = assets/*,images/*.png

# (list) Source files to exclude (let empty to not exclude anything)
source.exclude_exts = spec

# (list) List of directory to exclude (let empty to not exclude anything)
source.exclude_dirs = tests, bin, android_env, .git, .buildozer, .venv, tui, novels, venv, that, see, system, myenv, can

# (list) List of exclusions using pattern matching
#source.exclude_patterns = license,images/*/*.jpg

# (str) Application versioning (method 1)
version = 2.0.0

# (str) Application versioning (method 2)
# version.regex = __version__ = '['"]{1}([\d.]+)['"]{1}
# version.filename = %(source.dir)s/main.py

# (list) Application requirements
# curl_cffi is deliberately omitted: it is a compiled extension with no p4a
# recipe; sources/scriblehub.py imports it lazily and falls back to httpx.
requirements = python3,kivy==2.3.1,kivymd==2.0.0,httpx,beautifulsoup4,deep-translator,EbookLib,requests,idna,anyio,sniffio,certifi,charset-normalizer,arabic-reshaper,python-bidi

# (str) Custom source folders for requirements
# (Sets custom source for any requirements with recipes)
# requirements.source.kivy = ../../kivy

# (str) Presplash of the application
#presplash.filename = %(source.dir)s/data/presplash.png

# (str) Icon of the application
icon.filename = %(source.dir)s/gui/data/icon.png

# (str) Supported orientation
orientation = portrait

# (bool) Indicate if the application should be fullscreen
fullscreen = 0

# (bool) Indicate if the application should be a home app
home_app = False

# (bool) Indicate the android display cutout mode
#display_cutout = never

# -----------------------------------------------------------------------------
# Android specific
# -----------------------------------------------------------------------------

# (bool) Enable AndroidX support
android.enable_androidx = True

# (str) Android entry point, default is ok for Kivy-based app
#android.entrypoint = org.kivy.android.PythonActivity

# (str) The name of the activity to use
#android.activity_class_name = org.kivy.android.PythonActivity

# (str) Android app theme
#android.apptheme = "@android:style/Theme.NoTitleBar"

# (list) Java classes to add as activities to the manifest.
#android.add_activites = com.example.ExampleActivity

# (str) OUYA Console category. Should be one of GAME or APP
#android.ouya.category = GAME

# (str) Filename of OUYA Console icon. It must be a 732x412 png image.
#android.ouya.icon.filename = %(source.dir)s/data/ouya_icon.png

# (str) XML file to include as an intent filters in <activity> tag
#android.manifest.intent_filters =

# (str) launchMode to set for the main activity
#android.manifest.launch_mode = standard

# (str) screenOrientation to set for the main activity
#android.manifest.orientation = fullSensor

# (list) Android application meta-data to set (key=value format)
#android.meta_data =

# (str) Android prefix for the application id
#android.prefix =

# (list) Permissions
android.permissions = INTERNET,ACCESS_NETWORK_STATE,WAKE_LOCK

# (int) Target Android API, should be as high as possible.
android.api = 34

# (int) Minimum API your APK will support.
android.minapi = 21

# (int) Android SDK version to use
#android.sdk = 30

# (str) Android NDK version to use
#android.ndk = 25b

# (bool) Use Android private data storage (creates ~/.kivy)
#android.private_storage = True

# (str) Android NDK directory (if empty, it will be automatically downloaded.)
#android.ndk_path =

# (str) Android SDK directory (if empty, it will be automatically downloaded.)
#android.sdk_path =

# (str) ANT directory (if empty, it will be automatically downloaded.)
#android.ant_path =

# (bool) If True, then skip trying to update the Android sdk
#android.skip_update = False

# (bool) If True, then automatically accept SDK license
#android.accept_sdk_license = False

# (str) Android entry point, default is ok for Kivy-based app
#android.entrypoint = org.kivy.android.PythonActivity

# (str) Android app theme, default is ok for Kivy-based app
# android.apptheme = "@android:style/Theme.NoTitleBar"

# (bool) If True, then use the Android debug keystore to sign the debug apk
#android.debug_signing = True

# (str) The version of the Android NDK to use
#android.ndk = 23c

# (int) The Android SDK version to use
#android.sdk_version = 30

# (list) Android additional libraries to copy into libs/armeabi
#android.add_libs_armeabi = libs/android/*.so
#android.add_libs_armeabi_v7a = libs/android-v7/*.so
#android.add_libs_arm64_v8a = libs/android-v8/*.so
#android.add_libs_x86 = libs/android-x86/*.so
#android.add_libs_mips = libs/android-mips/*.so

# (bool) Indicate whether the screen should stay on
# Don't forget to add the WAKE_LOCK permission if you set this to True
android.wakelock = True

# (str) Path to a custom source file that will be used instead of the standard
# Android.py bootstrap
#android.bootstrap_py = paths

# (list) Android application meta-data to set (key=value format)
#android.meta_data =
#    com.google.android.gms.ads.APPLICATION_ID=ca-app-pub-XXXX

# (str) The port number used for AdB
#android.adb_port = 5554

# (bool) If True, the binary is run under an RTL (right-to-left) layout
#android.rtl = False

# (list) Android application meta-data to set (key=value format)
#android.manifest.orientation = portrait

# (int) The number of seconds to wait before checking for an update
#android.update_check_interval = 3600

# (bool) If True, the binary is run under an RTL (right-to-left) layout
#android.rtl = False

[buildozer]

# (int) Log level (0 = error only, 1 = info, 2 = debug (with command output))
log_level = 2

# (int) Display warning if buildozer is run as root (0 = False, 1 = True)
warn_on_root = 1

# (str) Path to build artifact storage, absolute or relative to spec file
#build_dir = ./.buildozer

# (str) Path to build output (i.e. .apk, .aab, .ipa) storage
#bin_dir = ./bin

# (str) Android arch to build for
android.archs = arm64-v8a, armeabi-v7a

# (int) Number of threads used for building the app
#android.num_threads = 2