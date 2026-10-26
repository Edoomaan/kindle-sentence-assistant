package org.kindlesentence.core;

import java.util.concurrent.CountDownLatch;
import java.util.concurrent.TimeUnit;
import javax.swing.SwingUtilities;

public final class ExplanationControllerTest {
    private static final class Request implements ExplanationRequest {
        final CountDownLatch entered = new CountDownLatch(1);
        final CountDownLatch release = new CountDownLatch(1);
        final String answer;
        volatile Thread worker;
        boolean cancelled;

        Request(String answer) { this.answer = answer; }

        public String execute() throws Exception {
            worker = Thread.currentThread();
            entered.countDown();
            if (!release.await(3, TimeUnit.SECONDS)) throw new AssertionError("test release missing");
            return answer;
        }

        public void cancel() { cancelled = true; }

        void finish() throws Exception {
            require(entered.await(2, TimeUnit.SECONDS), "worker started");
            release.countDown();
            worker.join(2000);
            require(!worker.isAlive(), "worker finished");
            SwingUtilities.invokeAndWait(() -> { });
        }
    }

    public static void main(String[] args) throws Exception {
        Request old = new Request("Old answer");
        Request fresh = new Request("Fresh answer");
        Request closing = new Request("Late answer");
        Request[] requests = {old, fresh, closing};
        int[] calls = {0};
        SelectionPreview[] view = new SelectionPreview[1];
        ExplanationController[] controller = new ExplanationController[1];
        SwingUtilities.invokeAndWait(() -> {
            view[0] = new SelectionPreview();
            controller[0] = new ExplanationController(view[0], text -> requests[calls[0]++]);
            controller[0].select("First selection");
            require(calls[0] == 0, "selection alone never sends a request");
            controller[0].setActive(true);
            controller[0].setActive(true);
            controller[0].select("First selection");
            require(calls[0] == 1, "repeated activation does not duplicate request");
            controller[0].select("Second selection");
            require(old.cancelled, "changing selection cancels previous request");
        });
        fresh.finish();
        old.finish();
        SwingUtilities.invokeAndWait(() -> {
            require("Fresh answer".equals(view[0].selectedText()), "old result cannot replace new answer");
            controller[0].select("Third selection");
            controller[0].setActive(false);
            require(closing.cancelled, "closing cancels request");
        });
        closing.finish();
        SwingUtilities.invokeAndWait(() -> {
            require("Third selection".equals(view[0].selectedText()), "closed card ignores late result");
            controller[0].clear();
            require(view[0].selectedText().isEmpty(), "teardown clears text");
        });
        System.out.println("Request lifecycle checks passed.");
    }

    private static void require(boolean value, String message) {
        if (!value) throw new AssertionError(message);
    }
}
