package org.kindlesentence.install;

import java.io.*;
import java.nio.file.*;
import java.util.*;
import java.util.zip.*;

public final class RegistrationTest {
    public static void main(String[] args) throws Exception {
        File dir = new File(args[0]);
        File source = new File(dir, "fixture.jar");
        byte[] originalClass = new byte[] {0, 42, -1, 8};
        try (ZipOutputStream zip = new ZipOutputStream(new FileOutputStream(source))) {
            zip.putNextEntry(new ZipEntry("reader_plugins.xml"));
            zip.write("<Plugins>\n<Plugin class=\"existing\"/>\n</Plugins>".getBytes("UTF-8"));
            zip.closeEntry();
            zip.putNextEntry(new ZipEntry("unchanged.class"));
            zip.write(originalClass);
            zip.closeEntry();
        }
        File output = new File(dir, "candidate.jar");
        Registration.patch(source, output);
        try (ZipFile zip = new ZipFile(output)) {
            byte[] body;
            try (InputStream in = zip.getInputStream(zip.getEntry("unchanged.class"))) {
                body = new byte[originalClass.length];
                if (in.read(body) != body.length) throw new AssertionError("Truncated class");
            }
            if (!Arrays.equals(originalClass, body) || zip.size() != 2) throw new AssertionError("Contents changed");
        }
        try {
            Registration.patch(source, output);
            throw new AssertionError("Existing output overwritten");
        } catch (IOException expected) { }
        try {
            Registration.main(new String[] { source.toString(), new File(dir, "unsupported.jar").toString() });
            throw new AssertionError("Unknown original accepted");
        } catch (IOException expected) { }
        try {
            Registration.patch(output, new File(dir, "twice.jar"));
            throw new AssertionError("Duplicate registration accepted");
        } catch (IOException expected) { }
        System.out.println("Registration tests passed");
    }
}
