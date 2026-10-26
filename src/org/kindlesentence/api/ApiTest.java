package org.kindlesentence.api;

import org.kindlesentence.core.ExplanationFailure;

public final class ApiTest {
    public static void main(String[] args) {
        try {
            new ChatRequest("It is raining cats and dogs.").execute();
            System.out.println("API test passed. Open a book and try Explain.");
        } catch (ExplanationFailure failure) {
            System.out.println(failure.getMessage());
            System.exit(1);
        } catch (Exception failure) {
            System.out.println("API test failed. Check settings and Wi-Fi.");
            System.exit(1);
        }
    }
}
