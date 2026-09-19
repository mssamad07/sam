package com.sam.assistant.ui

import android.app.Activity
import android.os.Bundle
import android.widget.TextView
import android.widget.Button
import android.widget.EditText
import android.widget.LinearLayout

/**
 * Mobile HUD UI Activity for Sam.
 * Clean, mobile-optimized conversational interface.
 */
class SamHUDActivity : Activity() {

    private lateinit var statusText: TextView
    private lateinit var responseText: TextView
    private lateinit var inputEdit: EditText
    private lateinit var sendButton: Button

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        val layout = LinearLayout(this).apply {
            orientation = LinearLayout.VERTICAL
            setPadding(32, 32, 32, 32)
        }

        statusText = TextView(this).apply {
            text = "Sam: Ready"
            textSize = 16f
        }
        layout.addView(statusText)

        responseText = TextView(this).apply {
            text = "Namaste Boss! Phone pe bhi aapka assistant ready hai."
            textSize = 18f
            setPadding(0, 24, 0, 24)
        }
        layout.addView(responseText)

        inputEdit = EditText(this).apply {
            hint = "Ask Sam anything..."
        }
        layout.addView(inputEdit)

        sendButton = Button(this).apply {
            text = "Send"
            setOnClickListener {
                val query = inputEdit.text.toString().trim()
                if (query.isNotEmpty()) {
                    responseText.text = "Sam is thinking..."
                    inputEdit.text.clear()
                }
            }
        }
        layout.addView(sendButton)

        setContentView(layout)
    }
}
