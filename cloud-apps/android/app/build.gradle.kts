plugins {
    id("com.android.application")
}

android {
    namespace = "com.amirwolf.mangacloud"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.amirwolf.mangacloud"
        minSdk = 24
        targetSdk = 34
        versionCode = ((findProperty("cloudVersionCode") as String?) ?: "1").toInt()
        versionName = (findProperty("cloudVersionName") as String?) ?: "1.0"
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }

    val mangaKeystore = rootProject.file("../../keys/manga-release.keystore")
    signingConfigs {
        create("release") {
            if (mangaKeystore.exists()) {
                storeFile = mangaKeystore
                storePassword = "manga-1398-rel"
                keyAlias = "manga"
                keyPassword = "manga-1398-rel"
                enableV1Signing = true
                enableV2Signing = true
                enableV3Signing = true
            }
        }
    }
    buildTypes {
        release {
            isMinifyEnabled = false
            if (mangaKeystore.exists())
                signingConfig = signingConfigs.getByName("release")
        }
    }
}
