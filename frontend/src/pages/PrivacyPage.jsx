export default function PrivacyPage() {
  return (
    <div className="space-y-6 max-w-3xl">
      <h1 className="text-2xl font-bold text-slate-800">Privacy Policy</h1>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 text-slate-700 space-y-4">
        <section>
          <h2 className="text-lg font-semibold text-slate-800 mb-2">
            1. Information We Collect
          </h2>
          <p>
            We collect information you provide directly to us, such as when you
            create an account, update your profile, or contact support.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-slate-800 mb-2">
            2. How We Use Your Information
          </h2>
          <p>
            We use the information we collect to provide, maintain, and improve
            our services, process transactions, and send you related
            information.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-slate-800 mb-2">
            3. Data Sharing and Disclosure
          </h2>
          <p>
            We do not sell your personal information. We may share your
            information with service providers who perform services on our
            behalf.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-slate-800 mb-2">
            4. Data Security
          </h2>
          <p>
            We implement reasonable security measures to protect your
            information from unauthorized access, alteration, or destruction.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-slate-800 mb-2">
            5. Contact Us
          </h2>
          <p>
            If you have questions about this Privacy Policy, please contact us
            at support@beepos.com.
          </p>
        </section>
      </div>
    </div>
  );
}
