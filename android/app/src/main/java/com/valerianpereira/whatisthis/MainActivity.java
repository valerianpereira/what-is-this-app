package com.valerianpereira.whatisthis;

import android.os.Bundle;
import android.view.WindowManager;
import android.widget.Toast;
import com.getcapacitor.BridgeActivity;

// The app is a single-screen SPA — there is no WebView history for the
// default back button to fall back through, so an unhandled press used to
// close the whole app immediately. window.androidBack() (app/index.html)
// closes whatever's open (a settings sheet, a paused round) and reports
// whether it did; only when it says there's nothing left open — home or
// onboarding — do we fall through to a press-again-to-exit confirmation, so
// one stray tap mid-game can't lose a child's progress.
public class MainActivity extends BridgeActivity {
    private long lastBackPressAt = 0;

    // A round is five seconds of looking at a picture with no touch, so the
    // screen timeout used to lock the phone mid-game.
    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
    }

    @Override
    public void onBackPressed() {
        getBridge().getWebView().evaluateJavascript(
            "window.androidBack && window.androidBack()",
            (result) -> {
                if (!"true".equals(result)) confirmExit();
            }
        );
    }

    private void confirmExit() {
        long now = System.currentTimeMillis();
        if (now - lastBackPressAt < 2000) {
            super.onBackPressed();
            return;
        }
        lastBackPressAt = now;
        Toast.makeText(this, "Press back again to exit", Toast.LENGTH_SHORT).show();
    }
}
