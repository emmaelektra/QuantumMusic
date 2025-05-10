// New OSC Receiver //

(
//////////////////////////////////////////////////////////
//  Listen on UDP port 9999 and dispatch OSC handlers  //
//////////////////////////////////////////////////////////

// 1. OSCdef for histogram_data
OSCdef(\recvHist, { |msg, time, addr|
    // msg.asArray = ["/histogram_data", val0, val1, ...]
    var hist = msg.asArray.drop(1);
    ("[SC] histogram_data: " ++ hist).postln;
}, '/histogram_data', nil, 8888);

// 2. OSCdef for current_channel_probs
OSCdef(\recvProbs, { |msg, time, addr|
    var probs = msg.asArray.drop(1);
    ("[SC] current_channel_probs: " ++ probs).postln;
}, '/current_channel_probs', nil, 8888);

// 3. OSCdef for measured_state
OSCdef(\recvState, { |msg, time, addr|
    var state = msg[1];
    ("[SC] measured_state: " ++ state).postln;
}, '/measured_state', nil, 8888);

"Ready to receive OSC on port 8888".postln;
)



// Boot the SuperCollider server
(
s.waitForBoot({
    // Define a SynthDef that will play a sound
    SynthDef(\playSound, { |freq = 440, amp = 0.5, dur = 0.5|
        var env = EnvGen.kr(Env.perc(0.01, dur), doneAction: 2);
        Out.ar(0, SinOsc.ar(freq, 0, amp) * env);
    }).add;

    // Create an OSC responder to handle messages from Python
    OSCdef(\dataReceiver, { |msg|
        // Extract parameters from the OSC message
        var freq = msg[1];  // Frequency
        var amp = msg[2];   // Amplitude
        var dur = msg[3];   // Duration
        Synth(\playSound, [\freq, freq, \amp, amp, \dur, dur]);
    }, '/play');
});
)

// SuperCollider: Drone SynthDef
(
SynthDef(\drone, {
    var freqs = \freqs.kr(Array.fill(16, 50));  // Up to 16 frequencies
    var amps = \amps.kr(Array.fill(16, 0.1));  // Amplitudes for each frequency
    var sig = Mix.fill(freqs.size, { |i|
        SinOsc.ar(freqs[i], 0, amps[i])  // Sine wave for each frequency
    });
    sig = sig * 0.1;  // Master volume
	    sig = Mix(sig) * 0.05;  // Sum all sine waves
    Out.ar(0, sig.dup);  // Send to stereo output
}).add;
)

(
SynthDef.new(\drone, {
	var freqs = \freqs.kr(Array.fill(16, { |i| 50 + (i * 20) }));  // Default frequency array
	var amps = \amps.kr(Array.fill(16, 0));  // Default amplitude array
	var sig = Array.fill(16, { |i|
		SinOsc.ar(freqs[i], 0, amps[i])  // Use indexed access for controls
	});
    sig = Mix(sig) * 0.05;  // Sum all sine waves and scale down
    sig = sig * 0.5;  // Scale down overall volume to avoid clipping
	sig = Limiter.ar(sig, 0.9);  // Clamp the output signal to avoid clipping

    Out.ar(0, sig.dup);  // Output stereo signal
}).add;
)

s.boot;
s.plotTree;


// DRONE SYNTH
(
SynthDef.new(\drone, {
	arg atk = 3.0, rel = 9, pan = 0, amp = 1;
	var freqs = \freqs.kr(Array.fill(16, { |i| 50 + (i * 60) }));  // Default frequency array
	var amps = \amps.kr(Array.fill(16, 0));  // Default amplitude array
	var envs, sig, freqAmps;
	envs = EnvGen.kr(Env.new([0, 1, 0], [atk, rel], [-1, 1]), doneAction: 2);

	// Use a fixed reference frequency (e.g., 1000 Hz) for scaling
	freqAmps = freqs.collect { |freq, i|
    var safeFreq = max(freq, 0.001);  // Ensure frequency is never zero
    amps[i] * (1000 / safeFreq).sqrt
};

	// Generate individual sine waves with independent envelopes
	sig = Array.fill(16, { |i|
		SinOsc.ar(freqs[i], 0, freqAmps[i]) * envs  // sine
		//Saw.ar(freqs[i],mul:freqAmps[i]) * envs

	});
	//sig = Pan2.ar(sig, pan, amp);
	sig = Mix(sig);  // Sum all sine waves
	//sig = sig * amp * envs;  // Apply global amplitude and envelope
	sig = sig * amp;  // Clamp the output signal to avoid clipping
	//sig = FreeVerb.ar(sig, mix: 0.0, room: 5, damp: 0, mul: 1.0, add: 0.0); // adding reverb

	Out.ar(0, sig.dup);  // Output stereo signal
}).add;
)
s.boot;
// DRONE OSC
(
x = OSCdef(\droneTrigger, { |msg|
	var freqs = msg[1..16];  // Extract frequencies
	var amps = msg[17..32];  // Extract amplitudes
	var amp = 0.15.exprand(0.2);  // Generate a random amplitude
	var pan = Pwhite(-0.8, 0.8, inf);
	Synth(\dronee_hist, [\freqs, freqs, \amps, amps, \amp, amp]);  // Create a new Synth for each message
	freqs.postln;
	amps.postln;
}, '/drone');
)
x.free;

// New attempt at a drone, this time a bit more interesting
(
SynthDef.new(\dronee, {
	arg freq1 = 69.05, freq2, freq3, amp = 5, det1 = 0.05, det2 = 0.05, atk = 2, sus = 0, rel = 3, c1 = 1,c2 = (-1), cf = 70, rq = 0.2, hpf = 70;
	var sig1, sig2, sig3, sig, env;
	env = EnvGen.kr(Env([0, 1, 1, 0], [atk, sus, rel], [c1, 0, c2]), doneAction:2);
	freq2 = freq1 + det1;
	freq3 = freq2 + det2;
	sig1 = Saw.ar(freq1);
	sig2 = Saw.ar(freq2)*LFTri.kr(0.05).range(0.6, 1);
	sig3 = Pulse.ar(freq3, LFTri.kr(0.5).range(0.95,1));
	sig = (sig1 + sig2 + sig3) * amp * env;
	//sig = BPF.ar(sig, cf, rq);
	sig = RLPF.ar(sig, hpf, mul:-20.dbamp);
	//sig = DelayN.ar(sig, delaytime: 1);
	//sig = FreeVerb.ar(sig, room: 10, damp: 5);
	Out.ar(0, sig.dup)
}).add
)

(
[58, 65, 68, 73].midicps.do{
	arg f;
	Synth(
		\dronee,
		[
			\freq, f,
			\amp, 0.25,
			\hpf, f * exprand(0.1,12),
			\cf, f * exprand(0.1,5),
			\rq, exprand(0.01, 0.5),
		]
	);
};
)

// DRONEE SYNTH

(
SynthDef(\dronee_hist, {
	arg amp = 20, det1 = 0.05, det2 = 0.05, atk = 3, rel = 9;
	var freqs, amps, sig, freqAmps, env;
	env = EnvGen.kr(Env.new([0, 1, 0], [atk, rel], [0, 1]), doneAction: 2);

	// Define 16 frequencies and amplitudes dynamically
	freqs = \freqs.kr(Array.fill(16, { |i| 50 + (i * 60) }));
	amps = \amps.kr(Array.fill(16, { |i| 0 }));  // Default amplitude array

		// Calculate frequency-dependent amplitude scaling
	freqAmps = freqs.collect { |freq, i|
		var safeFreq = max(freq, 0.001);  // Ensure frequency is never zero
		amps[i] * (1000 / safeFreq).sqrt  // Scale amplitude inversely with sqrt(freq)
	};

	// Create the signal for each frequency
	sig = Array.fill(16, { |i|
		var freq1 = freqs[i];
		var freq2 = freq1 + det1;
		var freq3 = freq2 + det2;
			var sig1 = Saw.ar(freq1, amps[i]);
			var sig2 = Saw.ar(freq2, amps[i]) * LFTri.kr(0.05).range(0.6, 1);
			var sig3 = Pulse.ar(freq3, LFTri.kr(0.05).range(0.95, 1), amps[i]);
		(sig1 + sig2 + sig3)
	});

	// Combine signals and apply a filter

	sig = RLPF.ar(sig, 70, mul:10.dbamp);  // Adjust cutoff frequency as needed
	sig = Mix(sig) * amp * env;
	Out.ar(0, sig.dup);
}).add;
)

// BUFFERS
~bGalton = Buffer.read(s, "/Users/emmasokoll/Documents/D&C/DC MA/QuantumMusic/Samples/Galton_box.wav");
~bGalton.play;
~bGalton.query;
s.sampleRate;

// PLAYBUF
(
SynthDef.new(\galton, {
	arg amp = 0.8, out = 0, buf, rate = 1, t_trig = 1, start = 0, loop = 0, da = 2;
	var sig;
	sig = PlayBuf.ar(2, buf, BufRateScale.kr(buf) * rate, t_trig, start, loop, doneAction: da);
	sig = sig * amp;
	Out.ar(out, sig);
}).add;
)

Synth.new(\galton, [\buf, ~bGalton.bufnum, \rate, 1]);
x = Synth.new(\galton, [\buf, ~bGalton.bufnum, \rate, 1, \start, s.sampleRate*4, \da, 0]);
x = Synth.new(\galton, [\buf, ~bGalton.bufnum, \loop, 1]);

Synth.new(\galton, [\buf, ~bGalton.bufnum, \rate, -7.midiratio])
Synth.new(\galton, [\buf, ~bGalton.bufnum, \rate, -10.midiratio])
Synth.new(\galton, [\buf, ~bGalton.bufnum, \rate, -13.midiratio])
Synth.new(\galton, [\buf, ~bGalton.bufnum, \rate, -15.midiratio])

x.set(\t_trig, 1);
x.free;
s.freeAll;

s.boot;

// BUFREAD
(
SynthDef.new(\galtonRd, {
	arg amp = 0.7, out = 0, buf, start, end, rate = 1;
	var sig, ptr;
	ptr = Phasor.ar(0, BufRateScale.kr(buf)*rate, start, end);
	sig = BufRd.ar(2, buf, ptr);
	sig = sig * amp;
	Out.ar(0, sig);
}).add;
)
x = Synth.new(\galtonRd, [\buf, ~bGalton.bufnum, \start, 0, \end, ~bGalton.numFrames-1]);
x.set(\start, ~bGalton.numFrames/2, \end, ~bGalton.numFrames-1);
x.set(\start, 200000, \end, 500000);
x.set(\rate, -1.midiratio);
x.free;
~bGalton.numFrames;
s.freeAll;

(
SynthDef.new(\galtonRdnoise, {
	arg amp = 0.7, out = 0, buf, start, end, freq = 1;
	var sig, ptr;
	ptr = LFNoise1.ar(freq).range(start, end);
	sig = BufRd.ar(2, buf, ptr);
	sig = sig * amp;
	Out.ar(0, sig);
}).add;
)
y = Synth.new(\galtonRdnoise, [\buf, ~bGalton.bufnum, \start, 0, \end, ~bGalton.numFrames-1, \freq, 1]);
y.free;

// STATE SOUND SYNTH
(
SynthDef(\measuredStateSound, {
    arg measuredState = 0, freq = 200, amp = 0.5, atk = 0.01, rel = 0.1;
    var env, sig;

    // Envelope with doneAction: 2 for automatic node cleanup
    env = EnvGen.kr(Env.new([0, 1, 0], [atk, rel], [-1, 1]), doneAction: 2);

    // Generate sine wave for the given frequency
    sig = SinOsc.ar(freq, 0, env);
	sig = sig * amp;

    // Output stereo signal
    Out.ar(0, sig.dup);
}).add;
)

// STATE SOUND OSC
(
~measuredState = Array.fill(4, 0);  // Initialize with zeros

~playSequentialNotes = { |measuredStateArray, duration = 1|
    Routine({<<
        measuredStateArray.do { |state, index|
            if (state == 1, {
                // Play a note only if the state is 1
                Synth(\water, [
                    \freq, 200 + (index * 100),  // Frequency based on index
                    \amp, 0.05                   // Amplitude
                ]);
            });
            duration.wait;  // Wait for the specified duration before the next note
        };
    }).play;
};

y = OSCdef(\measuredStateUpdate, { |msg|
    "OSC message received:".postln;
    msg.postln;  // Print the received OSC message for debugging

    // Extract measured state from the OSC message
    ~measuredState = msg[1..];  // Extract the list directly
    ~measuredState.postln;      // Print the extracted measured state

    // Play the measured state sequentially
    ~playSequentialNotes.(~measuredState, 1);  // 1-second delay between notes
}, '/measured_state');
)

// STATE SOUND OSC BUFFER
(
~measuredState = Array.fill(4, 0);  // Initialize with zeros

~playSequentialNotes = { |measuredStateArray, duration = 1|
    Routine({
        measuredStateArray.do { |state, index|
            if (state == 1, {
				Synth(\water, [
                    \freq, 200 + (index * 100),  // Frequency based on index
                    \amp, 0.5                   // Amplitude
				]);

            });
            duration.wait;  // Wait for the specified duration before the next note
        };
    }).play;
};

y = OSCdef(\measuredStateUpdate, { |msg|
    "OSC message received:".postln;
    msg.postln;  // Print the received OSC message for debugging

    // Extract measured state from the OSC message
    ~measuredState = msg[1..];  // Extract the list directly
    ~measuredState.postln;      // Print the extracted measured state

    // Play the measured state sequentially
    ~playSequentialNotes.(~measuredState, 1);  // 1-second delay between notes
}, '/measured_state');
)
s.freeAll;
y.free;

// GINO https://www.youtube.com/watch?v=4uxTSP2fXrw
(
SynthDef(\gino, {
    var sig, trig, env, freq;

    // Trigger signal
    trig = Dust.ar(5);

    // Random frequency modulation
    freq = TExpRand.ar(10, 430, trig) * TExpRand.ar(10, 430, trig / 30);
    sig = SinOsc.ar(0.10 * freq) * 1000;
    sig = SinOsc.ar(1.70 * sig * 1.3);

    // Amplitude modulation
    sig = sig * TExpRand.ar(1, ExpRand(10, 300), trig / (1 / 4));
    sig = sig.fold2 * 10;
    sig = Limiter.ar(sig, 0.8);

    // Envelope
    env = Env.perc(Rand(0.01, 0.1), Rand(0.1, 1.5));
    sig = sig * EnvGen.ar(env, doneAction: Done.freeSelf);

    // Filtering
    sig = RLPF.ar(sig,
        XLine.ar(ExpRand(4000, 6000), ExpRand(1000, 400) * TExpRand.ar(0.1, 43, trig * 3), Rand(0.001, 0.5)),
        ExpRand(0.1, 0.8)
    );
    sig = sig.fold2;
    sig = sig ! 2; // Stereo signal

    // Output
    sig = sig * (-40.dbamp);
    Out.ar(0, sig * 0.9); // Corrected output index
}).add;
)

// Water Drop TEO https://www.youtube.com/watch?v=zINXsV2hnJE

b = Buffer.readChannel(s, "/Users/emmasokoll/Documents/D&C/DC MA/QuantumMusic/Samples/water-drip-45622.wav", numFrames: 14840, channels: [0]);

c = Buffer.readChannel(s, "/Users/emmasokoll/Documents/D&C/DC MA/QuantumMusic/Samples/water-drop-85731.wav", channels: [0]);

d = Buffer.readChannel(s, "/Users/emmasokoll/Documents/D&C/DC MA/QuantumMusic/Samples/waterdrops-cave-echo-sounds-230896.wav", numFrames: 40000,channels: [0]);

b.play;
b.numFrames;
c.play;
d.play;

(
SynthDef(\water, {
	var sig, amp = 0.05, trig;
	//trig = Dust.ar(6);
	trig = SinOsc.ar(16+SinOsc.ar(30).range(1,1000)).lag(0.3);

	sig = GrainBuf.ar(1, trig,
		ExpRand(0.02, 3)*LFNoise0.ar(trig), // grain duration
		d, // buffer
		Rand(0.12, 4.5)/10, // playback rate
		LFNoise1.ar(0.7).range(0.01, 0.8).lag(0.3)
	);

	sig = Splay.ar(sig, center: SinOsc.ar(3));
	sig = sig*10.lag(0.03);
	sig = RLPF.ar(sig, XLine.ar(TExpRand.ar(1000, 10000, trig*3),
		TExpRand.ar(300, 1800, trig/2),
		1.8),
	TExpRand.ar(0.2, 0,5, trig)
	);

	sig = sig * amp * Env.perc(
		ExpRand(0.01, 0.6), // attack time
		ExpRand(0.5, 0.38) // release time

	).ar(Done.freeSelf);

	Out.ar(0, ExpRand(0.3, 0.9)*sig)
}).add;
)

(
Routine({
	loop({
			a = Synth(\water);
			2.wait
		})
}).play
)



















// GPT "gnarly" synth building blocks
(
SynthDef(\granularNoise, {
    var noise = PinkNoise.ar();
    var grains = GrainSin.ar(2, Impulse.kr(10), 0.02, LFNoise1.kr(10).range(200, 2000));
    Out.ar(0, (noise + grains) * 0.3);
}).add;
)

(
SynthDef(\feedbackNoise, {
    var sig = LocalIn.ar(2);
    sig = sig + SinOsc.ar(LFNoise1.kr(5).range(100, 2000)) * 0.2;  // Add oscillator to feedback
    sig = tanh(sig);  // Apply distortion
    LocalOut.ar(sig * 0.98);  // Feedback slightly reduced
    Out.ar(0, sig * 0.1);
}).add;
)

(
SynthDef(\ringModNoise, {
    var carrier = SinOsc.ar(200);  // Base frequency
    var modulator = SinOsc.ar(LFNoise1.kr(5).range(50, 500));  // Modulator frequency
    var sig = Ringz.ar(carrier * modulator, 500, 0.1);  // Ring modulation
    Out.ar(0, sig.dup * 0.3);
}).add;
)

(
SynthDef(\chaosNoise, {
    var chaos = Crackle.ar(2);  // Chaotic crackle sound
    var filtered = BRF.ar(chaos, LFNoise1.kr(2).range(200, 1000), 0.1);  // Band-reject filter
	Out.ar(0, filtered.dup * 0.3);
}).add;
)

(
SynthDef(\distortedDelay, {
    var noise = WhiteNoise.ar();
    var delay = CombC.ar(noise, 0.1, LFNoise1.kr(2).range(0.01, 0.1), 5);
    var distorted = tanh(delay * 10);  // Apply distortion
    Out.ar(0, distorted.dup * 0.3);
}).add;
)

(
SynthDef(\gnarlyOsc, {
    var sig = Saw.ar(LFNoise0.kr(5).range(100, 2000));  // Saw wave modulated by low-frequency noise
    sig = sig * 10;  // Boost amplitude for distortion
    sig = tanh(sig);  // Apply hard clipping distortion
    Out.ar(0, sig.dup * 0.3);
}).add;
)

(
SynthDef(\gnarlyNoise, {
    var noise = WhiteNoise.ar();  // Start with white noise
    var filtered = RLPF.ar(noise, LFNoise1.kr(4).range(200, 2000), 0.1);  // Dynamic resonant filter
    Out.ar(0, filtered.dup * 0.3);  // Output with reduced amplitude
}).add;
)

x = Synth.new(\granularNoise);
x = Synth.new(\feedbackNoise);
x = Synth.new(\ringModNoise);
x = Synth.new(\chaosNoise);
x = Synth.new(\distortedDelay);
x = Synth.new(\gnarlyOsc);
x = Synth.new(\gnarlyNoise);
x.free;
s.meter;
s.reboot;

s.quit;


