##  1 — Introduction and Scope (corrected transcription)

Hi.

In this session, I am going to explain **consecutive frames**.

---

##  2 — Variable Declarations and Setup (corrected transcription)

First, I have included the `includes` section.
Under the `variables` block, I am going to declare three variables.

One variable is for **Tester Present**.
The second is for **Programming Session Control**.
The third one is for **Write Data by Identifier (Write DID)**.

For consecutive frames, I am **not declaring them now**.
I will declare them only once, when I initialize the consecutive frames.

As of now, we consider only these three variables.

Then, in `on message 0x1E0`, which is the **input message**, I am declaring the message.
The DLC is set to `8`.
This means the number of bytes is eight.

Even if you do not mention the DLC explicitly, it is not an issue.

Then, the output message is `0x1E8`.
This output message is considered as the **response (RSP)**.

Next, we declare the bytes.
Byte by byte.

One byte, two bytes, three bytes, up to eight bytes.

Here, we are declaring that we are going to use **eight bytes of data**.

So this is the variable declaration we are doing here.

Only these variables are declared at this stage.
At runtime, if some variables are not used, they will be shown in green.

This includes the consecutive frames as well.
At this point, consecutive frames are not yet added.

That is all for the variable declaration.

When we move forward, if variables are unused, they will be highlighted in green.
Once we start using them, that indication will automatically disappear.

---

##  3 — Event Triggers: onKey vs onStart (corrected transcription)

Now I am going to start with `on key`, not `on start`.

When you press a specific key, the corresponding block will execute.
That is how `on key` works.

Inside `on key`, I am setting a **cyclic timer**.

I am giving **Tester Present**, because Tester Present should be sent cyclically, not just once.

So I am setting the timer to **2000 milliseconds**, which is two seconds.

Every two seconds, Tester Present will be sent continuously.
This indicates to the ECU that the tester is still present.

Similarly:

* `on key P` is used for **Programming Session Control**
* `on key W` is used for **Write DID**

When you press the write key, the write operation starts.

---

##  4 — Timer Configuration for Tester Present (corrected transcription)

When you press the key for Tester Present, the `on timer TesterPresent` block starts executing.

---

##  5 — Tester Present Message Construction (corrected transcription)

Inside the `on timer TesterPresent` block, we define the message content.

`message.byte(0)` is set accordingly.

Tester Present is defined as follows:

The length is `0x02`.
`message.byte(1)` is `0x3E`, which is the **Tester Present service ID**.
`message.byte(2)` is `0x80`.

Tester Present supports two subfunctions.
Here, I am using subfunction `0x80`.

This can vary from project to project.

I have already explained Tester Present in UDS separately.

After this, the remaining bytes are set to `0x00`.

So the full Tester Present request becomes:

`02 3E 80 00 00 00 00 00`

This is the Tester Present message.

We successfully initialized Tester Present earlier in the variables section.
Then, in the `on key` section, we triggered it.

This defines the trigger point.

Here, the input signal is sent, and the output is assigned to the message variable.

The Tester Present request is sent successfully.

---

##  6 — Programming Session Control Request (corrected transcription)

After Tester Present, we move to **Programming Session Control**.

Tester Present is written at the very beginning so that it keeps sending cyclically from the initial point.

That is the impact of declaring and defining Tester Present first.

Programming Session Control is implemented in a similar way.

The zeroth byte is `0x02`, followed by `0x10`, and then `0x02`.

This corresponds to Diagnostic Session Control – Programming Session.

You are already familiar with this.

Again, I have used some copy-paste here.

The request looks like:

`02 10 02 00 00 00 00 00`

---

##  7 — Write DID Request and Multi-Frame Need (corrected transcription)

Now we move to **Write DID**.

For example, `10 45 23 00 01 02`.

Here you can see that the payload is **more than eight bytes**.

Because the data length exceeds eight bytes, it cannot be sent in a single CAN frame.

So it requires **multi-frame transmission**, which involves flow control and consecutive frames.

This part is straightforward, but you must be prepared to handle multiple frames correctly.

For this reason, I am initializing an integer variable for **frame indexing**.

Since we are going to use more than one frame, we must explicitly manage them.

---

##  8 — First Frame and Consecutive Frame Structure (corrected transcription)

I am defining **Frame 1**.

In Frame 1, `message.byte(0)` is set to `0x21`.

`0x21` indicates the **first consecutive frame**.

The next frames will be `0x22`, `0x23`, and so on.

From byte 1 onward, we write the actual data:

`04 05 06 07 08 09 0A`

Similarly, we write as many frames as required.

Each frame function returns `0` or `1`.

Frame 1 is defined first.
Then we define Frame 2, Frame 3, and Frame 4.

I am copying and pasting the same structure for all frames.

All data types are declared as integers, because all CAPL data— including characters— is handled as integers.

There may be a mismatch between the PCI length and the total number of frames.
I will explain that separately.

For now, the main intention is to understand how **multiple frames are sent using CAPL**.

---

##  9 — Defining Frame Functions (Frame 1–4) (corrected transcription)

We have included four frames.

These four frames must be called by CAPL.

To do that, we must use an **on timer block**.

After Tester Present, Programming Session, and Write DID, execution does not directly jump to Frame 1, Frame 2, and so on.

Instead, it enters the **consecutive frame block**.

---

##  10 — Consecutive Frame Execution Logic (corrected transcription)

When the payload is larger than eight bytes, the ECU sends a **Flow Control** frame.

Once the flow control is received, execution jumps into the **consecutive frame block**.

Inside the consecutive frame block, we call:

* Frame 1
* Frame 2
* Frame 3
* Frame 4

Execution starts again from Frame 1, then Frame 2, then Frame 3, and finally Frame 4.

All frames are transmitted sequentially.

This successfully writes the data using consecutive frames.

The `on timer consecutive frame` block behaves like a function dispatcher.

It is simple and does not need to be overcomplicated.

Once all frames are sent, the entire input operation is completed.

---

##  11 — Output Message Handling (corrected transcription)

Now we move to output message handling.

If semicolons are used incorrectly inside consecutive frame blocks, errors will occur.

The output message should be `0x1E8`.

For Programming Session Control:

* A positive response is `50 02` on message `0x1E8`.

If we receive this, we print:
“Programming session activated successfully.”

Negative responses are handled using NRCs.

If `byte(0) == 0x7F`:

* NRC `0x12`: Sub-function not supported
* NRC `0x13`: Incorrect message length or invalid format

Priority handling is already managed by the embedded stack, so we do not need to handle it manually.

The same logic applies to Write DID.

A positive response for Write DID is `0x6E`.

If the response is not `0x6E`, then the write operation failed.

---

##  12 — Logging vs Trace Window (corrected transcription)

Trace windows are temporary.

Log files are permanent.

It is highly recommended to write important events into the log file.

In `on start`, you can log:

* Test cycle number
* Test duration
* Test purpose

Log files can be opened later and reviewed at any time.

---

##  13 — Timer Cancellation and Cleanup (corrected transcription)

Once a timer is started, it must be stopped explicitly.

This is the responsibility of the developer.

In `on stop measurement`, we cancel all active timers.

We cancel:

* Programming session timer
* Write DID timer
* Tester Present timer

Tester Present is cancelled last because it must continue until the end.

There is no keyword called `cancel timer cyclic`.

The correct syntax is simply `cancel timer <timerName>`.

---

##  14 — Compilation and Parser Errors (corrected transcription)

Parser errors are usually caused by:

* Spelling mistakes
* Syntax errors

They do not indicate logic errors.

For example:

* Missing characters in `cancel timer`
* Incorrect semicolon usage
* Missing quotation marks

Configuration errors are different.

A “no compiler configuration” error usually means:

* Incorrect project path
* Missing test module configuration

This is not a CAPL logic issue.

---

##  15 — Debugging Strategy (corrected transcription)

Debugging should be done step by step.

Remove errors one by one.

Parser errors first.
Then configuration warnings.

Unused response variables can be removed safely.

Using `RSP` instead of the output message variable is also valid.

---

##  16 — Final End-to-End Flow Recap (corrected transcription)

The complete flow is:

* Trigger using `on key` or `on start`
* Send Tester Present cyclically
* Send Programming Session Control
* Send Write DID
* Handle multi-frame transmission using consecutive frames
* Validate positive and negative responses
* Log results
* Stop timers properly

That is the complete CAPL flow for handling consecutive frames correctly.
