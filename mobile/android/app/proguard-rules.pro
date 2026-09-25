# Add project specific ProGuard rules here.
# Release builds currently ship with isMinifyEnabled = false (see app/build.gradle.kts),
# so these rules are not exercised yet - kept ready for when shrinking is turned on.

# kotlinx.serialization: keep serializer() for our @Serializable model classes.
-keepattributes *Annotation*, InnerClasses
-dontnote kotlinx.serialization.AnnotationsKt
-keepclassmembers class kotlin.Metadata {
    public <methods>;
}
-keep,includedescriptorclasses class de.ownai.app.**$$serializer { *; }
-keepclassmembers class de.ownai.app.** {
    *** Companion;
}
-keepclasseswithmembers class de.ownai.app.** {
    kotlinx.serialization.KSerializer serializer(...);
}
