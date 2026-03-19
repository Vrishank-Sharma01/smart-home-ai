package com.aegrome.luna2o


import android.Manifest
import android.content.Intent
import android.content.pm.PackageManager
import android.os.Bundle
import android.speech.RecognizerIntent
import android.widget.Button
import android.widget.TextView
import android.widget.Toast
import androidx.activity.result.contract.ActivityResultContracts
import androidx.appcompat.app.AppCompatActivity
import androidx.core.content.ContextCompat
import android.media.MediaRecorder
import android.os.Handler
import android.os.Looper
import android.speech.tts.TextToSpeech
import java.util.Locale
import android.net.Uri
import org.json.JSONObject
import android.provider.AlarmClock
import android.provider.Settings
import android.hardware.camera2.CameraManager
import com.google.firebase.database.FirebaseDatabase

class MainActivity : AppCompatActivity() {


    private lateinit var tts: TextToSpeech
    private lateinit var commandText: TextView
    private lateinit var speakButton: Button

    private lateinit var voiceOrb: VoiceOrbView

    private var cameraManager: CameraManager? = null
    private var cameraId: String? = null


    private val permissionLauncher =
        registerForActivityResult(ActivityResultContracts.RequestPermission()) { granted ->
            if (granted) {
                startVoiceInput()
            } else {
                Toast.makeText(this, "Microphone permission denied", Toast.LENGTH_SHORT).show()
            }
        }

    private val speechLauncher =
        registerForActivityResult(ActivityResultContracts.StartActivityForResult()) { result ->

            stopVoiceVisualizer()

            voiceOrb.updateVoiceLevel(0f)

            if (result.resultCode == RESULT_OK) {
                val data = result.data
                val resultList =
                    data?.getStringArrayListExtra(RecognizerIntent.EXTRA_RESULTS)

                if (!resultList.isNullOrEmpty()) {

                    val spokenText = resultList[0]

                    commandText.text = spokenText

                    processCommand(spokenText)
                }
            }
        }

    private var recorder: MediaRecorder? = null
    private val handler = Handler(Looper.getMainLooper())

    private val blockedApps = listOf(
        "com.digilocker.android",
        "net.one97.paytm",
        "com.google.android.apps.nbu.paisa.user",
        "in.org.npci.upiapp",
        "com.phonepe.app",
        "com.amazon.mShop.android.shopping"
    )

    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContentView(R.layout.activity_main)

        voiceOrb = findViewById(R.id.voiceOrb)
        commandText = findViewById(R.id.tvCommand)
        speakButton = findViewById(R.id.btnSpeak)

        tts = TextToSpeech(this) {
            if (it == TextToSpeech.SUCCESS) {
                tts.language = Locale.US
            }
        }

        speakButton.setOnClickListener {

            if (ContextCompat.checkSelfPermission(
                    this,
                    Manifest.permission.RECORD_AUDIO
                ) == PackageManager.PERMISSION_GRANTED
            ) {
                startVoiceInput()
            } else {
                permissionLauncher.launch(Manifest.permission.RECORD_AUDIO)
            }
        }

        cameraManager = getSystemService(CAMERA_SERVICE) as CameraManager
        cameraId = cameraManager?.cameraIdList?.get(0)


    }


    private fun askAI(question: String) {

        Thread {

            try {

                val url = java.net.URL("https://api.openai.com/v1/chat/completions")
                val connection = url.openConnection() as java.net.HttpURLConnection

                connection.requestMethod = "POST"
                connection.setRequestProperty("Authorization", "Bearer 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")
                connection.setRequestProperty("Content-Type", "application/json")
                connection.doOutput = true

                val jsonInput = """
                {
                  "model": "gpt-4.1-mini",
                  "messages": [
                    {"role": "user", "content": "$question"}
                  ]
                }
            """.trimIndent()

                connection.outputStream.write(jsonInput.toByteArray())

                val stream = if (connection.responseCode in 200..299) {
                    connection.inputStream
                } else {
                    connection.errorStream
                }

                val response = stream.bufferedReader().readText()

                val jsonObject = JSONObject(response)
                val reply = jsonObject
                    .getJSONArray("choices")
                    .getJSONObject(0)
                    .getJSONObject("message")
                    .getString("content")

                runOnUiThread {
                    commandText.text = reply
                    speak(reply)
                }

            } catch (e: Exception) {
                runOnUiThread {
                    speak("Error connecting to AI")
                }
            }

        }.start()
    }

    private fun startVoiceInput() {


        startVoiceVisualizer()

        voiceOrb.updateVoiceLevel(1f)
        val intent = Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH)

        intent.putExtra(
            RecognizerIntent.EXTRA_LANGUAGE_MODEL,
            RecognizerIntent.LANGUAGE_MODEL_FREE_FORM
        )

        intent.putExtra(
            RecognizerIntent.EXTRA_PROMPT,
            "Speak to LUNA"
        )

        speechLauncher.launch(intent)
    }

    private fun startVoiceVisualizer() {

        recorder = MediaRecorder().apply {
            setAudioSource(MediaRecorder.AudioSource.MIC)
            setOutputFormat(MediaRecorder.OutputFormat.THREE_GPP)
            setAudioEncoder(MediaRecorder.AudioEncoder.AMR_NB)
            setOutputFile(cacheDir.absolutePath + "/temp.3gp")

            prepare()
            start()
        }

        handler.post(object : Runnable {
            override fun run() {
                recorder?.let {

                    val amplitude = it.maxAmplitude / 2700f
                    voiceOrb.updateVoiceLevel(amplitude)

                    handler.postDelayed(this, 50)
                }
            }
        })
    }

    private fun stopVoiceVisualizer() {

        try {
            recorder?.apply {
                stop()
                reset()
                release()
            }
        }catch(e:Exception){
            e.printStackTrace()
        }

        recorder = null
        handler.removeCallbacksAndMessages(null)
        voiceOrb.updateVoiceLevel(0f)
    }

    private fun processCommand(command: String) {

        val lower = command.lowercase()

        // 🔥 SMART HOME CONTROL (SEND TO FIREBASE)

        if (
            lower.contains("turn on") ||
            lower.contains("turn off") ||
            lower.contains("add room") ||
            lower.contains("delete room")
        ) {

            val db = FirebaseDatabase.getInstance()
            val ref = db.getReference("commands")

            ref.setValue(lower)

            speak("Executing command")

            return
        }

        when {

            lower.startsWith("hello") || lower.startsWith("hi") -> {
                speak("Hello, how can I assist you?")
            }

            lower.contains("time") -> {
                val time = java.text.SimpleDateFormat("hh:mm a").format(java.util.Date())
                speak("The time is $time")
            }

            lower.contains("turn on flashlight") -> {

                speak("Turning on flashlight")

                try {
                    cameraManager?.setTorchMode(cameraId!!, true)
                } catch (e: Exception) {
                    speak("Flashlight not available")
                }
            }

            lower.contains("turn off flashlight") -> {

                speak("Turning off flashlight")

                try {
                    cameraManager?.setTorchMode(cameraId!!, false)
                } catch (e: Exception) {
                    speak("Flashlight not available")
                }
            }

            lower.contains("turn on wifi") || lower.contains("turn off wifi") -> {

                speak("Opening WiFi settings")

                val intent = Intent(Settings.ACTION_WIFI_SETTINGS)
                startActivity(intent)
            }

            lower.contains("turn on bluetooth") || lower.contains("turn off bluetooth") -> {

                speak("Opening Bluetooth settings")

                val intent = Intent(Settings.ACTION_BLUETOOTH_SETTINGS)
                startActivity(intent)
            }

            lower.contains("navigate") || lower.contains("direction") || lower.contains("go to") -> {

                var place = lower
                    .replace("navigate to", "")
                    .replace("navigate", "")
                    .replace("direction to", "")
                    .replace("direction", "")
                    .replace("go to", "")
                    .trim()

                if (place.isNotEmpty()) {

                    speak("Navigating to $place")

                    val encodedPlace = Uri.encode(place)

                    val intent = Intent(
                        Intent.ACTION_VIEW,
                        Uri.parse("https://www.google.com/maps/dir/?api=1&destination=$encodedPlace")
                    )

                    intent.setPackage("com.google.android.apps.maps")

                    startActivity(intent)

                } else {
                    speak("Where should I navigate?")
                }
            }

            lower.contains("play") -> {

                val query = lower.replace("play", "").trim()

                if (query.isNotEmpty()) {

                    speak("Playing $query on YouTube")

                    val encodedQuery = Uri.encode(query)

                    val intent = Intent(
                        Intent.ACTION_VIEW,
                        Uri.parse("https://www.youtube.com/results?search_query=$encodedQuery")
                    )

                    startActivity(intent)

                } else {
                    speak("What would you like me to play?")
                }
            }

            lower.contains("send whatsapp message") -> {

                speak("Opening WhatsApp")

                try {

                    val intent = Intent(Intent.ACTION_SEND)
                    intent.type = "text/plain"
                    intent.setPackage("com.whatsapp")

                    intent.putExtra(Intent.EXTRA_TEXT, "Hello from LUNA 🤖")

                    startActivity(intent)

                } catch (e: Exception) {

                    speak("WhatsApp is not installed")

                }
            }

            lower.contains("weather") || lower.contains("temperature") -> {

                var place = lower
                    .replace("weather", "")
                    .replace("temperature", "")
                    .replace("in", "")
                    .trim()

                if (place.isEmpty()) {
                    place = "my location"
                }

                speak("Showing weather for $place")

                val encodedPlace = Uri.encode("weather $place")

                val intent = Intent(
                    Intent.ACTION_VIEW,
                    Uri.parse("https://www.google.com/search?q=$encodedPlace")
                )

                startActivity(intent)
            }

            lower.contains("search") -> {

                val query = lower.replace("search", "").trim()

                if (query.isNotEmpty()) {

                    speak("Searching for $query")

                    val encodedQuery = Uri.encode(query)

                    val intent = Intent(
                        Intent.ACTION_VIEW,
                        Uri.parse("https://www.google.com/search?q=$encodedQuery")
                    )

                    startActivity(intent)

                } else {
                    speak("What would you like me to search?")
                }
            }

            lower.contains("open") -> {

                val appName = lower.replace("open", "").trim()

                openApp(appName)
            }

            lower.contains("set alarm") -> {

                stopVoiceVisualizer()

                speak("Setting alarm")

                val intent = Intent(AlarmClock.ACTION_SET_ALARM)

                intent.putExtra(AlarmClock.EXTRA_HOUR, 7)
                intent.putExtra(AlarmClock.EXTRA_MINUTES, 0)
                intent.putExtra(AlarmClock.EXTRA_MESSAGE, "Alarm from LUNA")

                intent.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK)

                if (intent.resolveActivity(packageManager) != null) {
                    startActivity(intent)
                } else {
                    speak("No alarm app found")
                }
            }



            lower.contains("remind me") -> {

                speak("Creating reminder")

                val intent = Intent(Intent.ACTION_INSERT).apply {
                    data = android.provider.CalendarContract.Events.CONTENT_URI
                    putExtra(android.provider.CalendarContract.Events.TITLE, "Reminder from LUNA")
                }

                if (intent.resolveActivity(packageManager) != null) {
                    startActivity(intent)
                } else {
                    speak("No calendar app found")
                }
            }

            lower.contains("what") ||
                    lower.contains("who") ||
                    lower.contains("explain") ||
                    lower.contains("define") ||
                    lower.contains("when") ||
                    lower.contains("how") ||
                    lower.contains("where") ||
                    lower.contains("why") ||
                    lower.contains("tell")-> {

                speak("Searching for the answer")

                val query = command.replace(" ", "+")

                val intent = Intent(Intent.ACTION_VIEW)
                intent.data = Uri.parse("https://www.google.com/search?q=$query")

                startActivity(intent)
            }

            else -> {
                askAI(command)
            }
        }
    }

    fun openApp(appName: String) {

        val pm = packageManager
        val apps = pm.getInstalledApplications(PackageManager.GET_META_DATA)

        for (app in apps) {

            val label = pm.getApplicationLabel(app).toString().lowercase()

            if (label.contains(appName.lowercase())) {

                if (blockedApps.contains(app.packageName)) {
                    speak("For security reasons I cannot open this app")
                    return
                }

                val intent = pm.getLaunchIntentForPackage(app.packageName)

                if (intent != null) {
                    startActivity(intent)
                    speak("Opening $appName")
                    return
                }
            }
        }

        speak("I couldn't find that app")
    }


    private fun speak(text: String) {
        tts.speak(text, TextToSpeech.QUEUE_FLUSH, null, null)
    }

}