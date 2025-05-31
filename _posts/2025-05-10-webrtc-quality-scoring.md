---
author:
    name: "Thinh Dang"
    avatar: "/assets/images/avatar.png"
    bio: "Experienced Fintech Software Engineer Driving High-Performance Solutions"
    location: "Viet Nam"
    email: "thinhdang206@gmail.com"
    links:
        -   label: "Linkedin"
            icon: "fab fa-fw fa-linkedin"
            url: "https://www.linkedin.com/in/thinh-dang/"
toc: true
toc_sticky: true
header:
    overlay_image:  /assets/images/webrtc-quality-scoring/banner.jpeg
    overlay_filter: 0.5
    teaser:  /assets/images/webrtc-quality-scoring/banner.jpeg
title: "Demystifying WebRTC Quality: A Deep Dive into the rtcscore Library and MOS Estimation"
tags:
    - WebRTC
    - Quality
    - MOS

---

# **Demystifying WebRTC Quality: A Deep Dive into the rtcscore Library and MOS Estimation**

## The Quest for Quality: Understanding User Experience in WebRTC

Web Real-Time Communication (WebRTC) has revolutionized how web applications enable direct peer-to-peer interaction, facilitating the streaming of audio, video, and arbitrary data between browsers without the need for intermediary servers for the media itself. In this landscape, the quality of these real-time interactions is not merely a feature but a cornerstone of user satisfaction and application viability. Subpar audio or video, frustrating delays, or disruptive glitches can quickly lead users to abandon a service. Indeed, a significant portion of quality issues often stem from user-side problems like poor network connectivity, making robust monitoring and assessment crucial.

At the heart of quantifying this user experience is the Mean Opinion Score (MOS). MOS is a widely recognized numerical metric that reflects the human-perceived overall quality of an audio or video session. It is typically expressed on a five-point scale, as detailed below:

| MOS Score | Perception |
| :---- | :---- |
| 5 | Excellent |
| 4 | Good |
| 3 | Fair |
| 2 | Poor |
| 1 | Bad |

*Table 1: Mean Opinion Score Scale and Corresponding Quality Perception. Data derived from.6 Generally, a MOS score around 4.3-4.5 is considered an excellent target, while quality below 3.5 often becomes unacceptable.*

Traditionally, MOS values were derived from subjective tests, where groups of human listeners and viewers would rate their experience. However, for the dynamic and scalable nature of modern WebRTC applications, such manual assessments are impractical. This has led to the development of objective MOS estimation algorithms, which predict the likely subjective score based on measurable network and media parameters. The rtcscore library, the focus of this discussion, falls into this category of objective MOS predictors. The International Telecommunication Union (ITU-T) provides standardized terminology for MOS in its P.800.1 recommendation, aiming to ensure consistent interpretation of these scores across different contexts.

The transition towards objective MOS estimation, as embodied by tools like rtcscore, is a direct response to the operational demands of WebRTC services. Continuous, real-time quality monitoring through subjective human testing is simply not feasible at scale. Algorithmic approaches provide an automated and scalable means to gauge user experience, enabling developers to identify issues, trigger adaptive behaviors, and ultimately enhance service reliability.

However, while MOS offers a convenient single-figure summary of quality, its interpretation requires some nuance. As an average score, it amalgamates the effects of numerous underlying factors. A "good" overall MOS might obscure specific deficiencies, such as excellent audio quality paired with poor video, or generally acceptable performance punctuated by brief but severe glitches. rtcscore itself acknowledges this by providing separate scores for audio and video.9 Therefore, while MOS is invaluable, a comprehensive understanding of quality often necessitates examining the constituent metrics that contribute to this score, a point underscored by the observation that even with zero packet loss, media quality can still be subpar due to other factors.

## Key Ingredients of WebRTC Quality: Essential Metrics Explained

The Mean Opinion Score, while a powerful indicator, is the outcome of a complex interplay of various underlying network conditions and media stream characteristics. The rtcscore library leverages several of these critical metrics to compute its quality estimations. Understanding these individual components is essential for any developer working with WebRTC and aiming to interpret or improve media quality.

### Packet Loss  

Packet loss occurs when data packets transmitted over the network fail to reach their intended destination. This is a common issue in IP networks, where data transmission often follows a "best-effort" mechanism. Common culprits include network congestion, where routers drop packets due to overload, signal corruption during transmission, or hardware malfunctions along the path. The impact on user experience can be severe, manifesting as choppy or distorted audio, freezing or pixelated video, or even complete loss of the media stream. WebRTC employs several strategies to mitigate packet loss, such as packet loss concealment (PLC), retransmission requests for critical data, and Forward Error Correction (FEC).

### Latency (Round Trip Time \- RTT)  

Latency, often measured as Round Trip Time (RTT), is the duration it takes for a data packet to travel from the sender to the receiver and for an acknowledgment (or response packet) to return to the sender. It is typically measured in milliseconds (ms). RTT is a critical performance metric, especially for conversational applications, as high latency introduces noticeable delays, making real-time interaction feel sluggish and unnatural. For optimal performance, an RTT below 100 ms is desirable. Values between 100-200 ms may be noticeable but often acceptable, while RTTs exceeding 200 ms generally lead to a degraded user experience, and very high RTTs (e.g., over 375 ms) can result in connection termination.

### Jitter & Jitter Buffer Delay  

Jitter refers to the variation in the arrival times of consecutive data packets, essentially the inconsistency in packet inter-arrival delay. While packets might be sent at a constant rate, network conditions can cause them to arrive unevenly. High jitter can lead to distorted audio (pops, clicks) and stuttering or freezing video, as the receiving application struggles to play out a smooth media stream.

To counteract jitter, WebRTC implementations use a jitter buffer. This buffer temporarily stores incoming packets, reorders them if necessary, and then plays them out at a steady rate, effectively smoothing out the variations in arrival times. The jitter buffer delay is the amount of time packets spend in this buffer. While the jitter buffer is crucial for maintaining smooth playback, it does add to the overall end-to-end latency. The jitterBufferDelay statistic, available via WebRTC's getStats() API, quantifies this added delay and is a direct input for some MOS calculation models, including the one used by rtcscore.

### Bitrate (Audio & Video)  

Bitrate is the amount of data used to represent a media stream per unit of time, typically expressed in bits per second (bps) or kilobits per second (kbps). Generally, a higher bitrate allows for better media quality—clearer audio and sharper, more detailed video—but at the cost of consuming more network bandwidth. There's a point of diminishing returns, however, where increasing bitrate further yields little perceptible improvement in quality.  

### Frame Rate and Resolution (Video)  

For video streams, two key parameters are frame rate and resolution. Frame rate, measured in frames per second (FPS), determines the smoothness of motion in the video. Low frame rates can make video appear jerky or cause it to freeze. Resolution, expressed as width and height in pixels (e.g., 1280x720 for 720p HD), dictates the level of detail and clarity in the video image. Achieving higher resolution and higher frame rates naturally requires higher bitrates to transmit the increased amount of visual information.

### Codecs (Opus for Audio; VP8, VP9, H.264 for Video)  

Codecs (coder-decoders) are algorithms or software responsible for compressing media data for efficient transmission and decompressing it for playback. The choice of codec significantly impacts the resulting quality for a given bitrate, as well as the computational load on the devices.

* **Opus**: The default audio codec in WebRTC, Opus is highly versatile, supporting a wide range of bitrates and offering excellent quality for both speech and music. It also includes features like built-in Forward Error Correction (FEC) and support for Discontinuous Transmission (DTX).
* **VP8**: An open-source video codec developed by Google, VP8 is well-suited for real-time communication due to its balance of quality and relatively low computational complexity. It's a common baseline codec in WebRTC.  
* **VP9**: Also developed by Google as a successor to VP8, VP9 offers significantly better compression efficiency, meaning it can deliver higher quality video at the same bitrate as VP8, or similar quality at a lower bitrate. This advantage is particularly noticeable at higher resolutions. The rtcscore library notes an assumption of approximately 20% improvement in encoding efficiency for VP9 compared to VP8 and H.264.
* **H.264 (AVC)**: A widely adopted video codec, H.264 provides a good balance of compression efficiency, video quality, and broad hardware support. It's also a mandatory-to-implement codec in WebRTC.

### Forward Error Correction (FEC)  

Forward Error Correction is a proactive technique used to combat packet loss. It involves sending redundant data along with the original media packets. This allows the receiver to reconstruct lost packets without needing to request a retransmission, which would introduce additional delay. FEC is particularly valuable in real-time scenarios where low latency is critical. The Opus audio codec has built-in FEC capabilities. The rtcscore library takes a boolean fec flag as an input for its audio quality model, indicating whether FEC is active.

### Discontinuous Transmission (DTX)  

Discontinuous Transmission is a bandwidth optimization technique primarily used for audio. It works by detecting periods of silence in a conversation and significantly reducing or temporarily halting the transmission of audio packets during these silent intervals. When speech resumes, transmission returns to normal. This can lead to substantial bandwidth savings, especially in multi-party conferences where only one person is typically speaking at a time. The Opus codec supports DTX.23 Similar to FEC, rtcscore accepts a boolean dtx flag for its audio model.

It is important to recognize that these metrics are not isolated; they often influence one another. For instance, high network congestion can simultaneously lead to increased RTT, higher jitter, and more packet loss. If significant video packets are lost, the decoder might request a new keyframe (an I-frame), causing a temporary spike in bitrate. This interconnectedness means that a single underlying network problem can manifest as degradation across multiple quality indicators, all contributing to a lower MOS.

Furthermore, the rtcscore library's inclusion of "expected" versus "actual" parameters for video characteristics (like expectedWidth/expectedHeight and expectedFrameRate) suggests a nuanced approach to quality assessment. It implies that perceived quality is not solely determined by the raw characteristics of the received stream but also by how these characteristics compare to an ideal or intended presentation. For example, if a video is received at a lower resolution than expected and needs to be upscaled, or if frames are dropped relative to the source frame rate, rtcscore likely penalizes these discrepancies. This highlights that factors like video scaling and frame consistency are integral to the perceived quality.

Finally, the presence of boolean flags for FEC and DTX in rtcscore's input parameters indicates that the underlying quality models adjust their calculations based on whether these techniques are active. FEC, while consuming some extra bandwidth by sending redundant data, provides resilience against packet loss. DTX, while adding some processing complexity for voice activity detection and comfort noise generation, saves bandwidth during silence. The rtcscore model likely modifies its baseline expectations or impairment calculations accordingly—for instance, being more tolerant to raw packet loss if FEC is enabled, or not penalizing low audio bitrates during periods when DTX is active and silence is detected. This demonstrates an attempt by the library to be context-aware in its quality estimation.

## Introducing rtcscore: Your JavaScript Co-Pilot for MOS Estimation

In the complex world of WebRTC media quality, developers often seek tools that can simplify the assessment process. The rtcscore library emerges as such a tool: a JavaScript library specifically designed to estimate the Mean Opinion Score (MOS) for real-time audio and video communications, providing a score on the familiar 1 to 5 scale. Its primary purpose is to offer developers a programmatic way to gauge the perceived quality of WebRTC streams. This capability is invaluable for building applications that can automatically monitor call quality, assist in diagnosing issues, or even adapt their behavior in real-time based on the estimated quality—for example, by notifying users of poor conditions or suggesting a switch to an audio-only call.

The rtcscore library employs distinct methodologies for audio and video quality estimation, exposed through a single, straightforward API function named score().

* For **audio scoring**, rtcscore utilizes a **modified E-Model approach**.9 The E-Model, standardized by the ITU-T in recommendation G.107, is a computational model widely used for transmission planning and voice quality assessment.  
* For **video scoring**, the library relies on **logarithmic regression** formulas. These formulas were developed based on data collected from a limited set of subjective tests, aiming to correlate measurable video parameters with perceived quality.

This dual-method approach reflects a pragmatic design choice. The E-Model is a well-established and comprehensive framework for voice quality, but its full implementation can be quite complex. A "modified" E-Model, as used by rtcscore, likely simplifies this by focusing on the most impactful parameters that are readily obtainable in a WebRTC environment, particularly with the Opus audio codec. This makes the audio scoring more tractable for a client-side JavaScript library.

On the other hand, video quality perception is notoriously multifaceted, influenced by a wide array of interacting factors such as bitrate, resolution, frame rate, codec type, and even the nature of the video content itself (e.g., a static presentation versus a high-motion scene). Developing a purely theoretical, universally accurate parametric model for video MOS is exceedingly challenging. Thus, rtcscore's adoption of a data-driven logarithmic regression model, even if based on "limited collected data", offers a more flexible and empirically grounded starting point. Logarithmic functions are often suitable for modeling perceptual quality, as they can capture the common phenomenon of diminishing returns—for instance, where incremental increases in bitrate yield progressively smaller improvements in perceived quality.

It is important to note a characteristic of rtcscore regarding the scope of its output: the library is designed to provide instantaneous quality snapshots based on the input parameters provided at a specific moment. It does not, by itself, handle the aggregation of these scores over extended periods or across multiple participants in a conference call. This means that if developers require an overall quality score for an entire call session, or wish to track quality trends over time, they are responsible for implementing the necessary logic to collect multiple rtcscore outputs and then average or otherwise process them. This design choice keeps the library focused on its core competency of MOS estimation from a given set of metrics, while allowing developers the flexibility to define their own aggregation strategies tailored to their specific application needs.

## Under the Hood: A Deep Dive into rtcscore's Logic (Based on Described Functionality)

The rtcscore library is architected around a primary function, typically invoked as score(stats). This function accepts an object containing distinct sets of parameters for audio and/or video streams. Internally, it processes these inputs through separate logic pathways to derive audioMos and videoMos values, returning them in an object like { audio: audioMos, video: videoMos }.

### Audio Scoring Logic: The Modified E-Model Adaptation

The audio scoring mechanism in rtcscore is rooted in the E-Model, a computational model defined by the ITU-T G.107 recommendation. The E-Model calculates a transmission quality rating, known as the R-factor, which typically ranges from 0 to 100\. A higher R-factor indicates better quality. The fundamental E-Model equation is often expressed as:  

**R=Ro​−Is​−Id​−Ie−eff​+A**

where:

* Ro​: Represents the basic signal-to-noise ratio under ideal conditions.  
* Is​: Represents impairments that occur simultaneously with the speech signal.  
* Id​: Represents impairments due to delay.  
* Ie−eff​: Represents effective equipment impairments, including those from codecs and packet loss.  
* A: Is an "advantage factor," reflecting user expectations or tolerance, often set to 0 for VoIP.

Given rtcscore's "modified" approach, it likely employs a simplified version of this model, such as the one described by the formula **R=R0​−Icodec​−Ipacketloss​−Idelay​**. This simplification focuses on the most critical and measurable impairments in a WebRTC context.

The components are likely handled as follows:

* **R0​ (Base Factor)**: This is probably a constant representing the maximum achievable R-factor before any impairments are considered. Simplified E-Models often set R0​ to a value like 93.2, accounting for inherent signal conversion losses. The rtcscore logic would initialize its R-value calculation with this base.  
* **Icodec​ or Ie​ (Equipment Impairment Factor \- Codec)**: The E-Model assigns specific impairment values based on the audio codec used. Since rtcscore's audio inputs do not explicitly request an audio codec type, it's reasonable to assume it's optimized for Opus, the WebRTC default. The provided bitrate parameter might influence this factor, or it could be used to adjust expectations if Discontinuous Transmission (DTX) is enabled. If dtx: true, the library might ignore the bitrate for impairment calculations during silence or add a small fixed penalty for DTX operation itself, as DTX inherently alters the continuous nature of the audio stream to save bandwidth.  
* **Ipacketloss​ or Ipl​ (Impairment due to Packet Loss)**: This impairment is derived from the packetLoss percentage input. The E-Model provides mechanisms to translate a packet loss percentage into an R-factor degradation, typically a non-linear relationship where the impact becomes more severe with increasing loss. A crucial aspect here is the FEC (Forward Error Correction) flag. If FEC: true, the detrimental effect of a given packetLoss percentage on the R-factor is mitigated. The E-Model can account for this through a "packet-loss robustness factor" (Bpl​), which is higher for codecs or configurations with effective FEC or Packet Loss Concealment (PLC). `rtcscore` likely implements a conditional logic to reduce the packet loss penalty when FEC is active.  
* **Idelay​ (Impairment due to Delay)**: This component is calculated from the roundTripTime (RTT) and bufferDelay inputs. The E-Model typically considers one-way delay. Thus, the provided RTT is likely halved, and the bufferDelay (representing jitter buffer delay) is added to this to estimate the effective one-way mouth-to-ear delay. The relationship between this cumulative delay and the corresponding impairment value (Idelay​) is non-linear, with impairment increasing sharply at higher delay values.  
* **A (Advantage Factor)**: This factor, representing user tolerance for impairments under certain conditions (e.g., mobile calls), is often set to 0 in VoIP contexts for a more conservative quality estimate. rtcscore most likely omits this factor or uses a fixed value of 0\.

Once the final R-factor is computed by subtracting the impairment values from R0​, it is converted into a MOS value (typically 1 to 5). A common formula for this conversion is:  
**MOS=1+0.035×R+R×(R−60)×(100−R)×7×10−6**  
This formula is applied for R values between 0 and 100, and the resulting MOS is then clamped to the 1-5 range. rtcscore would implement such a mapping.  

The "modified" nature of the E-Model in rtcscore suggests a practical adaptation. It likely prioritizes parameters that are directly and reliably obtainable from the WebRTC getStats() API, such as packetLoss, roundTripTime, and jitterBufferDelay. More complex E-Model inputs like specific room noise levels, send/receive loudness ratings (SLR/RLR), or detailed D-factors, which are not standard getStats() outputs, are probably simplified or incorporated as fixed assumptions within the R0​ or default codec impairment (Ie​) values.9 This approach aligns with the goal of making the library usable in typical client-side WebRTC applications without requiring extensive environmental calibration.

### Video Scoring Logic: Logarithmic Regression

For video quality, rtcscore employs a logarithmic regression model.9 This statistical approach predicts video MOS based on a formula derived from fitting a curve to subjective test data, where users rated video quality under various conditions. The "logarithmic" aspect often implies that some input parameters, like bitrate, have a diminishing return on quality improvement—doubling a very low bitrate might significantly improve MOS, but doubling an already high bitrate might yield a much smaller perceptible gain.

The input parameters for video 9 are likely incorporated into the regression formula as follows:

* **bitrate**: A primary predictor. The model will likely include a term like c1​×log(bitrate), where c1​ is a coefficient.  
* **packetLoss**: Higher packet loss will decrease the MOS, possibly through a term like −c2​×packetLoss.  
* **codec (VP8, VP9, H.264)**: This is a categorical variable. The model might apply different baseline adjustments or coefficients based on the codec. rtcscore documentation notes that VP9 is considered approximately 20% more efficient than VP8 or H.264. This could translate to an additive bonus in the MOS calculation for VP9 or a multiplicative factor applied to its effective bitrate.  
* **width, height (received) & expectedWidth, expectedHeight (rendering)**: The model likely considers both the absolute resolution (e.g., width × height) and any scaling involved. A scaling factor, perhaps (received pixels / expected pixels), could be calculated. If this ratio is less than 1 (indicating upscaling, which can cause blurriness), it might penalize the score.43 The absolute resolution itself interacts with bitrate requirements.  
* **frameRate (received) & expectedFrameRate (source)**: Similar to resolution, the model probably uses the absolute frameRate and a factor representing dropped frames (e.g., frameRate / expectedFrameRate). Frame rates falling significantly below the expectedFrameRate or a minimum acceptable threshold would likely incur a penalty.  
* **roundTripTime & bufferDelay**: While these are more dominant in audio quality perception, their inclusion as inputs for the video model is noteworthy. High delay and jitter can be symptomatic of network instability that leads to other video-specific issues not fully captured by bitrate or frame rate alone, such as increased likelihood of frame freezes or the need for more aggressive encoder adaptations. The regression model might have identified a statistical correlation between these delay metrics and subjectively perceived video quality, even if their direct perceptual impact on video (unlike audio) is less about interactivity and more about stream stability and consistency.

Conceptually, the regression formula might resemble:

**VideoMOS=intercept+k1​log(bitrate)−k2​⋅packetLoss+k3​⋅codec\_factor+k4​⋅resolution\_factor+k5​⋅framerate\_factor−k6​⋅delay\_factor+**…  

The specific coefficients (ki​) would be those determined from the "limited collected data" mentioned in the library's description.9 The final computed video MOS is then clamped to the 1-5 scale.  

The reliance of the video model on "limited collected data" implies that its accuracy could vary depending on the type of video content being assessed (e.g., talking head conference vs. screen sharing vs. high-motion video). Regression models perform best on data similar to their training set. Users should be mindful that the video MOS is an estimate, and its precision may be content-dependent.

Hypothetically, the score.js file would contain internal functions such as calculateAudioRValue(audioStats), rFactorToMos(rValue), and calculateVideoMos(videoStats), along with various helper functions for specific impairment calculations.

## Using rtcscore: A Practical Guide

The rtcscore library is designed for ease of use, primarily exposing a single function, score(), which takes an object containing parameters for the audio and/or video streams to be evaluated.

**Input Parameters for score()**

The main score() function expects an object that can have an audio property, a video property, or both. Each of these properties should be an object containing the relevant metrics for that media type. The table below details the input parameters as described in the rtcscore documentation 9:

| Media | Parameter | Type | Unit/Range | Description |
| :---- | :---- | :---- | :---- | :---- |
| Audio | packetLoss | Number | 0-100 (%) | Percentage of audio packets lost. |
| Audio | bitrate | Number | 0-200000 (bps) | Bitrate for audio transmission. (May be interpreted differently if DTX is true) |
| Audio | roundTripTime | Number | ms | Network delay's impact on experience. |
| Audio | bufferDelay | Number | ms | Reception delay (primarily jitter buffer) impact. |
| Audio | fec | Boolean | true/false | Opus Forward Error Correction enabled? |
| Audio | dtx | Boolean | true/false | Opus Discontinuous Transmission enabled? |
| Video | packetLoss | Number | 0-100 (%) | Percentage of video packets lost. |
| Video | bitrate | Number | bps (e.g., 0-5000000+) | Bitrate for video transmission. Higher is generally better. *.9* |
| Video | roundTripTime | Number | ms | Network delay's impact. |
| Video | bufferDelay | Number | ms | Reception delay (jitter buffer) impact. |
| Video | codec | String | "VP8"/"VP9"/"H264" | Video codec used. VP9 assumed \~20% more efficient by the model. |
| Video | width | Number | pixels | Resolution width of the received video. |
| Video | height | Number | pixels | Resolution height of the received video. |
| Video | expectedWidth | Number | pixels | Ideal rendering width. If not provided, width is assumed. |
| Video | expectedHeight | Number | pixels | Ideal rendering height. If not provided, height is assumed. |
| Video | frameRate | Number | fps | Frames received per second. |
| Video | expectedFrameRate | Number | fps | Expected frames per second (source). If not provided, frameRate is assumed. |

*Table 2: rtcscore Input Parameters. Derived from.*

**Interpreting the Output**

The score() function returns an object containing the estimated MOS for audio and/or video, for example: { audio: 4.2, video: 4.0 }. Each score is a numerical value between 1 and 5\. To understand the qualitative meaning of these scores, refer back to Table 1 (MOS Scale and Quality Perception).

**Example Usage Snippet**

Here's a basic example adapted from the rtcscore documentation 9, demonstrating how to use the library:

```js

// Assuming 'score' is the imported function from the rtcscore library  
const currentStats \= {  
  audio: {  
    packetLoss: 2,      // 2% packet loss  
    roundTripTime: 50,  // 50 ms RTT  
    bufferDelay: 20,    // 20 ms jitter buffer delay  
    fec: true,          // FEC is enabled  
    dtx: false,         // DTX is disabled  
    bitrate: 32000      // 32 kbps audio bitrate  
  },  
  video: {  
    packetLoss: 1,      // 1% packet loss  
    bitrate: 1200000,   // 1.2 Mbps video bitrate  
    roundTripTime: 50,  // 50 ms RTT  
    codec: 'VP9',       // Using VP9 codec  
    width: 1280,        // Received video width 1280px  
    height: 720,        // Received video height 720px  
    frameRate: 30,      // Receiving 30 FPS  
    // expectedWidth, expectedHeight, expectedFrameRate, bufferDelay could also be provided  
  }  
};

const qualityScores = score(currentStats);

if (qualityScores.audio !== undefined) {  
  console.log('Estimated Audio MOS:', qualityScores.audio.toFixed(1));  
}  
if (qualityScores.video !== undefined) {  
  console.log('Estimated Video MOS:', qualityScores.video.toFixed(1));  
}
```

In a real application, the values provided in the currentStats object would typically be derived from WebRTC's native statistics API.

**Sourcing Input Metrics: The WebRTC getStats() API**

WebRTC provides a powerful mechanism for developers to access a wide array of statistical information about an ongoing peer connection through the RTCPeerConnection.getStats() method. This API returns a report containing various statistics objects, from which the inputs for rtcscore can be derived.

Key RTCStats dictionary types relevant for populating rtcscore's input object include:

* **RTCInboundRtpStreamStats**: This object provides statistics for received RTP streams (both audio and video).  
  * **Packet Loss**: Can be calculated over an interval using packetsLost and packetsReceived. The formula packetLossPercent \= (delta\_packetsLost / (delta\_packetsReceived \+ delta\_packetsLost)) \* 100 is commonly used. It's important to note that packetsLost might only update upon receipt of RTCP Sender/Receiver Reports, so interval-based calculations are generally more reliable than relying on instantaneous values.
  * **Bitrate**: Calculated from bytesReceived over a time interval: bitrate \= (delta\_bytesReceived \* 8\) / delta\_seconds.  
  * **Frame Rate (for video)**: The framesPerSecond property can be used directly if available, or calculated from framesDecoded over an interval.  
  * **Jitter Buffer Delay**: rtcscore uses bufferDelay. While RTCInboundRtpStreamStats provides a jitter metric, the jitterBufferDelay (often an accumulated value that needs to be averaged over jitterBufferEmittedCount or similar for an interval value) is more directly related to the delay added by the jitter compensation mechanism, which is what E-Model type calculations typically require.
  * **Codec**: The codecId property links to an RTCCodecStats object, which contains the mimeType (e.g., "audio/opus", "video/vp9") to identify the codec..
* **RTCIceCandidatePairStats**: This object provides statistics about the active ICE candidate pair being used for communication.  
  * **Round Trip Time**: The currentRoundTripTime property (in seconds, needs conversion to ms) can be used for rtcscore's roundTripTime input.49 Alternatively, RTT can also be found in remote-inbound-rtp stats for an outgoing stream.

Developers need to periodically call getStats(), iterate through the results, identify the relevant statistics objects (often by type and kind), and then compute the specific metrics in the format required by rtcscore. This often involves calculating deltas between successive getStats() calls to determine rates like packet loss percentage or bitrate over specific intervals.

The rtcscore library effectively serves as an abstraction layer on top of the raw and sometimes voluminous getStats() API. It translates a curated set of low-level network and media metrics into a high-level, human-understandable quality score (MOS). This significantly simplifies the task of quality assessment for developers who may not be experts in the intricacies of the E-Model or video quality regression techniques.

One important consideration arises from rtcscore's "expected" resolution and frame rate parameters for its video model (expectedWidth, expectedHeight, expectedFrameRate). The standard getStats() API primarily reports on the characteristics of the *received* stream (e.g., framesDecoded, actual resolution of the track). It doesn't inherently convey what the application *intended* to display or what the original source characteristics were before any network-induced adaptations by the sender. Therefore, for rtcscore to leverage these "expected" parameters effectively, the application itself may need to manage this state—perhaps through signaling or configuration—and pass these values to the library. This implies an additional layer of application-specific logic to fully utilize the nuances of rtcscore's video quality estimation.

## Beyond rtcscore: Holistic WebRTC Quality Monitoring

While rtcscore provides a valuable and convenient way to estimate Mean Opinion Scores for audio and video streams, it represents one component within a broader strategy for comprehensive WebRTC quality monitoring and management. Achieving consistently high-quality real-time communication often requires a more holistic approach.

Effective WebRTC quality management should be viewed as a proactive and continuous process, rather than a one-time check or a single metric assessment. rtcscore can play a crucial role in this by forming part of an automated feedback loop. For instance, applications can use the real-time MOS estimates from rtcscore to trigger adaptive behaviors: alerting users to poor network conditions, suggesting a switch to an audio-only mode to conserve bandwidth, dynamically adjusting encoding parameters on the sender side, or logging detailed quality data for offline analysis by operations teams. This shifts the paradigm from passive monitoring to active, real-time quality management, thereby enhancing the user experience dynamically.

The importance of collecting and analyzing a diverse range of metrics cannot be overstated. While rtcscore focuses on a specific set of inputs to derive MOS, the full getStats() API in WebRTC offers a wealth of over 170 different statistics. Monitoring a broader array of these metrics—such as detailed jitter buffer statistics, specific codec-related counters (e.g., pliCount, nackCount), or ICE candidate pair state changes—can provide deeper insights into the root causes of quality degradation. Furthermore, incorporating mechanisms for users to provide direct subjective feedback on call quality can complement objective measurements, as individual perception of quality can sometimes vary even under similar network conditions.

It's also beneficial to correlate WebRTC quality data with broader business objectives. For example, understanding how call quality impacts user engagement, session duration, or task completion rates can provide valuable context for prioritizing quality improvements and investments.

The field of Quality of Experience (QoE) assessment is continually evolving. While rtcscore leverages a modified E-Model for audio and logarithmic regression for video, alternative models and approaches also exist. For instance, some research points to other models, like a Deterministic QoE model (DQX), potentially outperforming the traditional E-model in specific WebRTC scenarios, particularly concerning the impact of delay. Awareness of this evolving landscape helps position rtcscore as a practical tool while acknowledging ongoing advancements in QoE science.

A practical aspect of using any MOS estimation algorithm, including those within rtcscore, is understanding its output in the context of its inputs. While rtcscore conveniently abstracts the complex calculations of the E-Model and regression formulas, if it returns a low MOS, the developer's next step is often to determine *why* the score is low. This requires looking at the raw input metrics that were fed into rtcscore—was it high packet loss, excessive RTT, insufficient bitrate, or a combination of factors? The library provides the "what" (the estimated MOS), but the "why" often lies in the underlying statistics. Therefore, rtcscore is most effectively used in conjunction with the monitoring of these fundamental metrics to enable robust troubleshooting and targeted quality improvements.

## Conclusion: Empowering Your WebRTC Applications with Quality Insights

The rtcscore JavaScript library offers a valuable and accessible means for developers to estimate the Mean Opinion Score (MOS) for audio and video streams within their WebRTC applications. By implementing a modified E-Model for audio and a logarithmic regression-based approach for video, rtcscore translates complex sets of network and media parameters into a single, understandable metric of perceived quality. This abstraction simplifies a critical aspect of WebRTC development, allowing for automated quality assessment without requiring deep expertise in the underlying psychoacoustic or visual perception models.

The ability to programmatically measure and monitor quality is fundamental to building and maintaining successful WebRTC services. Tools like rtcscore empower developers to move beyond anecdotal evidence of quality issues and towards data-driven insights. By understanding the factors that influence user-perceived quality—such as packet loss, latency, jitter, bitrate, and codec performance—and by having a means to quantify their collective impact, development teams can more effectively diagnose problems, optimize performance, and ultimately deliver a superior user experience.

As real-time communication continues to be a vital component of modern web applications, the emphasis on quality will only grow. Actively measuring, monitoring, and acting upon quality metrics is no longer a luxury but a necessity. Libraries like rtcscore are instrumental in this endeavor, providing a practical step towards demystifying and managing the intricacies of WebRTC media quality.

For developers looking to integrate MOS estimation into their projects, the rtcscore library is available on GitHub. Engaging with such tools and the broader WebRTC community can further enhance understanding and drive innovation in delivering high-quality real-time interactions.

## Interactive Quality Explorer

Understanding audio quality in WebRTC applications is crucial for delivering excellent user experiences. The `rtcscore` library provides a sophisticated approach to estimating Mean Opinion Score (MOS) using the E-Model, a standardized method for assessing voice quality in telecommunications.

Below is an interactive demonstration that shows how various network conditions affect WebRTC audio quality. You can adjust parameters like packet loss, round-trip time, and jitter buffer delay to see their real-time impact on the quality score.

<div style="width: 100%; height: 800px; border: 1px solid #ddd; border-radius: 8px; overflow: hidden; margin: 20px 0;">
    <iframe 
        src="/assets/htmls/webrtc-quality-scoring.html" 
        width="100%" 
        height="100%" 
        frameborder="0"
        style="border: none;">
        Your browser does not support iframes. 
        <a href="/assets/htmls/webrtc-quality-scoring.html" target="_blank">View the interactive demo in a new window</a>
    </iframe>
</div>

### Understanding the E-Model

The E-Model works as a "penalty box" system, starting with a perfect base score and subtracting penalties for various impairments:

- **Packet Loss**: Even small amounts can severely impact quality
- **Delay**: Both network RTT and jitter buffer delay contribute
- **Codec Impairment**: Different codecs have inherent quality characteristics
- **Forward Error Correction (FEC)**: Can mitigate packet loss effects

### Key Takeaways

1. **Packet Loss is Critical**: Even 1-2% packet loss can noticeably degrade audio quality
2. **Delay Accumulates**: Network delay plus jitter buffer delay both contribute to the penalty
3. **FEC Helps**: Forward Error Correction can significantly reduce packet loss penalties
4. **Non-linear Relationship**: The R-Factor to MOS conversion is not linear, making quality perception complex

The interactive tool above demonstrates these principles in action, showing how the `rtcscore` library calculates quality metrics for real-world WebRTC applications.

## **Works cited**

1. [WebRTC API](https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API)  
2. WebRTC API \- MDN Web Docs \- Mozilla, accessed May 31, 2025, [https://developer.mozilla.org/en-US/docs/Web/API/WebRTC\_API](https://developer.mozilla.org/en-US/docs/Web/API/WebRTC_API)  
3. 7 Tips for WebRTC Monitoring \- Cyara, accessed May 31, 2025, [https://cyara.com/blog/tips-for-webrtc-monitoring/](https://cyara.com/blog/tips-for-webrtc-monitoring/)  
4. WebRTC 102: \#5 Understanding Call Quality \- Dyte.io, accessed May 31, 2025, [https://dyte.io/blog/webrtc-call-quality/](https://dyte.io/blog/webrtc-call-quality/)  
5. Mean Opinion Score (MOS) revisited: Methods and applications, limitations and alternatives \- Stefan Winkler, accessed May 31, 2025, [https://stefan.winklerbros.net/Publications/mmsj2016.pdf](https://stefan.winklerbros.net/Publications/mmsj2016.pdf)  
6. What is a Mean Opinion Score (MOS)? | Twilio, accessed May 31, 2025, [https://www.twilio.com/docs/glossary/what-is-mean-opinion-score-mos](https://www.twilio.com/docs/glossary/what-is-mean-opinion-score-mos)  
7. Mean Opinion Score (MOS) \- Techabulary, accessed May 31, 2025, [https://www.techabulary.com/m/mos/](https://www.techabulary.com/m/mos/)  
8. How to Measure VoIP Quality with MOS Score \- NetBeez, accessed May 31, 2025, [https://netbeez.net/blog/voip-and-mos-score/](https://netbeez.net/blog/voip-and-mos-score/)  
9. ggarber/rtcscore: JS Library to estimate the Mean Opinion Score (MOS) for Real Time audio & video communications \- GitHub, accessed May 31, 2025, [https://github.com/ggarber/rtcscore](https://github.com/ggarber/rtcscore)  
10. How to calculate MOS? | WebRTC for Developers, accessed May 31, 2025, [https://www.webrtc-developers.com/how-to-calculate-mos/](https://www.webrtc-developers.com/how-to-calculate-mos/)  
11. Itu-T: Mean Opinion Score (MOS) Terminology | PDF | Electronics \- Scribd, accessed May 31, 2025, [https://www.scribd.com/document/421826091/ITU](https://www.scribd.com/document/421826091/ITU)  
12. Packet Loss | BlogGeek.me, accessed May 31, 2025, [https://bloggeek.me/webrtcglossary/packet-loss/](https://bloggeek.me/webrtcglossary/packet-loss/)  
13. What is Packet Loss? | dolby.io, accessed May 31, 2025, [https://optiview.dolby.com/resources/blog/streaming/what-is-packet-loss/](https://optiview.dolby.com/resources/blog/streaming/what-is-packet-loss/)  
14. www.imperva.com, accessed May 31, 2025, [https://www.imperva.com/learn/performance/round-trip-time-rtt/\#:\~:text=Round%2Dtrip%20time%20(RTT),load%20time%20and%20network%20latency.](https://www.imperva.com/learn/performance/round-trip-time-rtt/#:~:text=Round%2Dtrip%20time%20\(RTT\),load%20time%20and%20network%20latency.)  
15. What is RTT? \- Round Trip Time in Networking Explained \- AWS, accessed May 31, 2025, [https://aws.amazon.com/what-is/rtt-in-networking/](https://aws.amazon.com/what-is/rtt-in-networking/)  
16. www.ir.com, accessed May 31, 2025, [https://www.ir.com/guides/what-is-network-jitter\#:\~:text=What%20exactly%20is%20network%20jitter,or%20not%20implementing%20packet%20prioritization.](https://www.ir.com/guides/what-is-network-jitter#:~:text=What%20exactly%20is%20network%20jitter,or%20not%20implementing%20packet%20prioritization.)  
17. WebRTC and Buffers \- GetStream.io, accessed May 31, 2025, [https://getstream.io/resources/projects/webrtc/advanced/buffers/](https://getstream.io/resources/projects/webrtc/advanced/buffers/)  
18. Define reception time for jitterBufferDelay stat · Issue \#549 · w3c/webrtc-stats \- GitHub, accessed May 31, 2025, [https://github.com/w3c/webrtc-stats/issues/549](https://github.com/w3c/webrtc-stats/issues/549)  
19. Tweaking WebRTC video quality: unpacking bitrate, resolution and frame rates, accessed May 31, 2025, [https://bloggeek.me/tweaking-webrtc-video-quality-unpacking-bitrate-resolution-and-frame-rates/](https://bloggeek.me/tweaking-webrtc-video-quality-unpacking-bitrate-resolution-and-frame-rates/)  
20. Uncovering the Power of Discontinuous Transmission \- Lenovo, accessed May 31, 2025, [https://www.lenovo.com/us/en/glossary/discontinuous-transmission/](https://www.lenovo.com/us/en/glossary/discontinuous-transmission/)  
21. VP8 Video Codec \- Library of Congress, accessed May 31, 2025, [https://www.loc.gov/preservation/digital/formats/fdd/fdd000578.shtml](https://www.loc.gov/preservation/digital/formats/fdd/fdd000578.shtml)  
22. WebRTC Media Resilience \- GetStream.io, accessed May 31, 2025, [https://getstream.io/resources/projects/webrtc/advanced/media-resilience/](https://getstream.io/resources/projects/webrtc/advanced/media-resilience/)  
23. Opus Discontinuous Transmission (DTX) \- What is it and how does it work? \- GetStream.io, accessed May 31, 2025, [https://getstream.io/resources/projects/webrtc/advanced/dtx/](https://getstream.io/resources/projects/webrtc/advanced/dtx/)  
24. An Adaptive Bitrate Switching Algorithm for Speech Applications in the Context of WebRTC, accessed May 31, 2025, [https://researchrepository.universityofgalway.ie/server/api/core/bitstreams/8539360a-d806-4eab-b62b-8c163d5ca539/content](https://researchrepository.universityofgalway.ie/server/api/core/bitstreams/8539360a-d806-4eab-b62b-8c163d5ca539/content)  
25. What Is The VP8 Codec? Streaming Optimized | Coconut©, accessed May 31, 2025, [https://www.coconut.co/articles/what-is-vp8-codec](https://www.coconut.co/articles/what-is-vp8-codec)  
26. VP9 vs. H.264 \- Cloudinary, accessed May 31, 2025, [https://cloudinary.com/guides/video-formats/vp9-vs-h-264](https://cloudinary.com/guides/video-formats/vp9-vs-h-264)  
27. VP9 \- Wikipedia, accessed May 31, 2025, [https://en.wikipedia.org/wiki/VP9](https://en.wikipedia.org/wiki/VP9)  
28. What is H.264? How it Works, Applications & More \- Gumlet, accessed May 31, 2025, [https://www.gumlet.com/learn/what-is-h264/](https://www.gumlet.com/learn/what-is-h264/)  
29. What is H.264 video encoding? \- Black Box, accessed May 31, 2025, [https://www.blackbox.co.uk/gb-gb/page/38313/Resources/Technical-Resources/Black-Box-Explains/AV/What-is-H264-video-encoding](https://www.blackbox.co.uk/gb-gb/page/38313/Resources/Technical-Resources/Black-Box-Explains/AV/What-is-H264-video-encoding)  
30. FEC (Forward Error Correction) \- BlogGeek.me, accessed May 31, 2025, [https://bloggeek.me/webrtcglossary/fec/](https://bloggeek.me/webrtcglossary/fec/)  
31. Making sense of getStats in WebRTC \- BlogGeek.me, accessed May 31, 2025, [https://bloggeek.me/getstats/](https://bloggeek.me/getstats/)  
32. WebRTC Stats \- Telnyx's Developer Documentation, accessed May 31, 2025, [https://developers.telnyx.com/docs/voice/webrtc/ios-sdk/stats](https://developers.telnyx.com/docs/voice/webrtc/ios-sdk/stats)  
33. Monitoring VoIP Call Quality Using Improved Simplified E-model \- \- MURAL \- Maynooth University Research Archive Library, accessed May 31, 2025, [https://mural.maynoothuniversity.ie/id/eprint/5965/1/DM-Monitoring-VoIP.pdf](https://mural.maynoothuniversity.ie/id/eprint/5965/1/DM-Monitoring-VoIP.pdf)  
34. 20.2 E-MODEL-BASED VOICE QUALITY ESTIMATION \- VoIP Voice and Fax Signal Processing \- O'Reilly Media, accessed May 31, 2025, [https://www.oreilly.com/library/view/voip-voice-and/9780470227367/ch020-sec002.html](https://www.oreilly.com/library/view/voip-voice-and/9780470227367/ch020-sec002.html)  
35. ITU-T G.107 | PIP Store, accessed May 31, 2025, [https://store.accuristech.com/pip/standards/itu-t-g-107?product\_id=2838625](https://store.accuristech.com/pip/standards/itu-t-g-107?product_id=2838625)  
36. ITU g-107 http://Certificate.Moscow, accessed May 31, 2025, [http://www.certificate.net/Portals/1/Standards/ITU/g-107.doc](http://www.certificate.net/Portals/1/Standards/ITU/g-107.doc)  
37. Quality-of-Experience driven configuration of WebRTC services through automated testing \- CNR Iris, accessed May 31, 2025, [https://iris.cnr.it/bitstream/20.500.14243/390943/1/prod\_437176-doc\_156634.pdf](https://iris.cnr.it/bitstream/20.500.14243/390943/1/prod_437176-doc_156634.pdf)  
38. Quality-based Video Bitrate Control for WebRTC-based Tele- conference Services \- IS\&T | Library, accessed May 31, 2025, [https://library.imaging.org/admin/apis/public/api/ist/website/downloadArticle/ei/34/9/IQSP-333](https://library.imaging.org/admin/apis/public/api/ist/website/downloadArticle/ei/34/9/IQSP-333)  
39. github.com, accessed May 31, 2025, [https://github.com/ggarber/rtcscore/blob/develop/src/score.js](https://github.com/ggarber/rtcscore/blob/develop/src/score.js)  
40. VoIP Evaluation \- IEEE 802, accessed May 31, 2025, [https://www.ieee802.org/20/Contribs/C802.20-05-36r1.doc](https://www.ieee802.org/20/Contribs/C802.20-05-36r1.doc)  
41. E-model Improvement for Speech Quality Evaluation Including Codecs Tandeming \- CORE, accessed May 31, 2025, [https://core.ac.uk/download/pdf/10672599.pdf](https://core.ac.uk/download/pdf/10672599.pdf)  
42. Delivering Superior VoIP Quality over Broadband \- HPE Aruba Networking, accessed May 31, 2025, [https://arubanetworking.hpe.com/assets/so/SO\_Delivering-Superior-VoIP-Quality-Over-Broadband.pdf](https://arubanetworking.hpe.com/assets/so/SO_Delivering-Superior-VoIP-Quality-Over-Broadband.pdf)  
43. Application of Optimized Adaptive Neuro-Fuzzy Inference for High Frame Rate Video Quality Assessment \- MDPI, accessed May 31, 2025, [https://www.mdpi.com/2076-3417/15/9/5018](https://www.mdpi.com/2076-3417/15/9/5018)  
44. MOS vs. bitrate for different frame rate and resolutions where Ice is characterised to have low SI and high TI. \- ResearchGate, accessed May 31, 2025, [https://www.researchgate.net/figure/MOS-vs-bitrate-for-different-frame-rate-and-resolutions-where-Ice-is-characterised-to\_fig2\_263337973](https://www.researchgate.net/figure/MOS-vs-bitrate-for-different-frame-rate-and-resolutions-where-Ice-is-characterised-to_fig2_263337973)  
45. Identifiers for WebRTC's Statistics API \- W3C, accessed May 31, 2025, [https://www.w3.org/TR/webrtc-stats/](https://www.w3.org/TR/webrtc-stats/)  
46. "packetsLost" and "jitter" stats only updated when RTCP SR or RR is sent \- WebRTC \- Monorail, accessed May 31, 2025, [https://bugs.chromium.org/p/webrtc/issues/detail?id=8804](https://bugs.chromium.org/p/webrtc/issues/detail?id=8804)  
47. RTCInboundRtpStreamStats: kind property \- Web APIs | MDN, accessed May 31, 2025, [https://developer.mozilla.org/en-US/docs/Web/API/RTCInboundRtpStreamStats/kind](https://developer.mozilla.org/en-US/docs/Web/API/RTCInboundRtpStreamStats/kind)  
48. RTCInboundRtpStreamStats \- Web APIs | MDN, accessed May 31, 2025, [https://developer.mozilla.org/en-US/docs/Web/API/RTCInboundRtpStreamStats](https://developer.mozilla.org/en-US/docs/Web/API/RTCInboundRtpStreamStats)  
49. RTCIceCandidatePairStats \- Web APIs | MDN, accessed May 31, 2025, [https://developer.mozilla.org/en-US/docs/Web/API/RTCIceCandidatePairStats](https://developer.mozilla.org/en-US/docs/Web/API/RTCIceCandidatePairStats)  
50. RTCIceCandidatePairStats: availableOutgoingBitrate property \- Web APIs | MDN, accessed May 31, 2025, [https://developer.mozilla.org/en-US/docs/Web/API/RTCIceCandidatePairStats/availableOutgoingBitrate](https://developer.mozilla.org/en-US/docs/Web/API/RTCIceCandidatePairStats/availableOutgoingBitrate)  
51. The Impact of Network Impairments on the QoE of WebRTC applications: A Subjective study \- UniCA IRIS, accessed May 31, 2025, [https://iris.unica.it/bitstream/11584/348629/4/post-2022-09%20QoMEX%20-%20Impact%20Network%20QoE%20WebRTC.pdf](https://iris.unica.it/bitstream/11584/348629/4/post-2022-09%20QoMEX%20-%20Impact%20Network%20QoE%20WebRTC.pdf)  
52. Gustavo Garcia ggarber \- GitHub, accessed May 31, 2025, [https://github.com/ggarber](https://github.com/ggarber)