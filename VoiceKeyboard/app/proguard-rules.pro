-keep class org.tensorflow.** { *; }
-keep class com.microsoft.onnxruntime.** { *; }
-keepclassmembers class * {
    @org.tensorflow.lite.annotations.UsedByReflection *;
}
-dontwarn org.tensorflow.**
-dontwarn com.microsoft.onnxruntime.**
