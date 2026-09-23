plugins {
    id("com.android.application")
    id("org.jetbrains.kotlin.android")
    id("com.chaquo.python")
}

android {
    namespace = "com.amirwolf.mangatranslator"
    compileSdk = 35

    defaultConfig {
        applicationId = "com.amirwolf.mangatranslator"
        minSdk = 24
        targetSdk = 34
        versionCode = 17
        versionName = "1.7"

        val buildAbis = ((findProperty("appAbis") as String?)
            ?: "arm64-v8a,armeabi-v7a")
            .split(",").map { it.trim() }.filter { it.isNotEmpty() }
        ndk {
            abiFilters += buildAbis
        }

    }

    packaging {
        jniLibs.useLegacyPackaging = false
    }

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_17
        targetCompatibility = JavaVersion.VERSION_17
    }
    kotlinOptions { jvmTarget = "17" }

    buildTypes {
        release {
            isMinifyEnabled = false
        }
    }
}


val engineRoot = rootProject.projectDir.parentFile
tasks.register<Copy>("copyEngineSources") {
    from(engineRoot) { include("manga.py", "manga_app.py") }
    into("src/main/assets/engine")
}
tasks.named("preBuild") { dependsOn("copyEngineSources") }


chaquopy {
    sourceSets {
        getByName("main") {
            exclude("rapidocr/models/*.onnx")
            exclude("rapidocr/models/*.onnx.*")
            exclude("**/__pycache__/**")
        }
    }
    defaultConfig {
        version = "3.10"
        buildPython = listOf(
            (findProperty("chaquopyBuildPython") as String?) ?: "python3")
        pip {
            install("numpy==1.26.2")
            install("opencv-python==4.5.1.48")
            install("pillow")
            install("shapely")
            install("arabic-reshaper")
            install("python-bidi==0.4.2")
            install("pyyaml")
            install("requests")
            install("six")
            install("tqdm")
            install("omegaconf")
            install("colorlog")
        }
    }
}

dependencies {
    implementation("com.microsoft.onnxruntime:onnxruntime-android:1.20.0")
    implementation("com.google.mlkit:text-recognition:16.0.1")
    implementation("com.google.mlkit:text-recognition-japanese:16.0.1")
    implementation("com.google.mlkit:text-recognition-korean:16.0.1")
    implementation("com.google.mlkit:text-recognition-chinese:16.0.1")
    implementation("androidx.core:core-ktx:1.13.1")
    implementation("androidx.appcompat:appcompat:1.7.0")
    implementation("androidx.recyclerview:recyclerview:1.3.2")
    implementation("com.google.android.material:material:1.12.0")
}
