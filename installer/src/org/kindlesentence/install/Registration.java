package org.kindlesentence.install;

import java.io.*;
import java.security.MessageDigest;
import java.util.*;
import java.util.zip.*;

public final class Registration {
    private static final String ORIGINAL = "a575b93abf58a812c4a88028ce74d86d73b6ed360cd88d55c53b5c73c6df71ce";
    private static final String ENTRY = "    <Plugin class=\"org.kindlesentence.nativeui.ExplainPlugin\" jar=\"/mnt/us/extensions/sentence-assistant/explain-preview.jar\" />\n";

    public static void main(String[] args) throws Exception {
        if (args.length == 1 && "--probe".equals(args[0])) {
            System.out.println("sentence-installer-ready");
            return;
        }
        if (args.length != 2) throw new IOException("Expected original and output paths");
        File source = new File(args[0]);
        if (!ORIGINAL.equals(digest(source))) throw new IOException("Unsupported original JAR");
        patch(source, new File(args[1]));
    }

    static String digest(File file) throws Exception {
        MessageDigest md = MessageDigest.getInstance("SHA-256");
        try (InputStream in = new FileInputStream(file)) {
            byte[] buf = new byte[8192];
            int n;
            while ((n = in.read(buf)) != -1) md.update(buf, 0, n);
        }
        StringBuilder result = new StringBuilder();
        for (byte b : md.digest()) result.append(String.format("%02x", b & 255));
        return result.toString();
    }

    private static byte[] read(ZipFile zip, ZipEntry entry) throws IOException {
        try (InputStream in = zip.getInputStream(entry);
             ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            byte[] buf = new byte[8192];
            int n;
            while ((n = in.read(buf)) != -1) {
                if (out.size() + n > 32 * 1024 * 1024) throw new IOException("Entry too large");
                out.write(buf, 0, n);
            }
            return out.toByteArray();
        }
    }

    static void patch(File source, File output) throws IOException {
        if (!output.createNewFile()) throw new IOException("Output already exists");
        try (ZipFile input = new ZipFile(source)) {
            ZipEntry xml = input.getEntry("reader_plugins.xml");
            if (xml == null) throw new IOException("Registration XML missing");
            String old = new String(read(input, xml), "UTF-8");
            int close = old.indexOf("</Plugins>");
            if (close < 0 || close != old.lastIndexOf("</Plugins>") || old.contains("org.kindlesentence.")) {
                throw new IOException("Unexpected registration XML");
            }
            byte[] updated = (old.substring(0, close) + ENTRY + old.substring(close)).getBytes("UTF-8");
            Set<String> names = new HashSet<String>();
            try (ZipOutputStream out = new ZipOutputStream(new FileOutputStream(output))) {
                Enumeration<? extends ZipEntry> entries = input.entries();
                while (entries.hasMoreElements()) {
                    ZipEntry entry = entries.nextElement();
                    String name = entry.getName();
                    if (!names.add(name) || name.toUpperCase(Locale.US).matches(".*\\.(SF|RSA|DSA|EC)$")) {
                        throw new IOException("Duplicate or signed archive");
                    }
                    ZipEntry copy = new ZipEntry(name);
                    if (entry.getTime() >= 0) copy.setTime(entry.getTime());
                    if (entry.getComment() != null) copy.setComment(entry.getComment());
                    out.putNextEntry(copy);
                    out.write("reader_plugins.xml".equals(name) ? updated : read(input, entry));
                    out.closeEntry();
                }
            }
            try (ZipFile check = new ZipFile(output)) {
                if (check.size() != names.size()) throw new IOException("Entry count changed");
                for (String name : names) {
                    byte[] expected = "reader_plugins.xml".equals(name) ? updated : read(input, input.getEntry(name));
                    if (!Arrays.equals(expected, read(check, check.getEntry(name)))) {
                        throw new IOException("Candidate contents differ");
                    }
                }
            }
        }
    }
}
