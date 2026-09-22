pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositories {
        google()
        mavenCentral()
        maven("https://chaquo.com/maven")
    }
}

rootProject.name = "MangaTranslator"
include(":app")
